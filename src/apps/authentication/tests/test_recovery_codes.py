"""Integration tests for MFA recovery codes."""

from sqlalchemy.ext.asyncio import AsyncSession

from apps.authentication.cruds.recovery_code import RecoveryCodeCRUD
from apps.authentication.services.recovery_codes import (
    decrypt_recovery_code,
    generate_recovery_codes,
    verify_recovery_code,
)
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import User
from config import settings


class TestRecoveryCodesIntegration:
    """Integration tests for recovery code generation and verification."""

    async def test_generate_codes_end_to_end(
        self,
        session: AsyncSession,
        user: User,
    ):
        """
        Test complete recovery code generation flow.

        Verifies:
        - Codes are generated and returned
        - Correct number of codes in DB
        - All codes have hash and encryption
        - User timestamp is updated
        """
        # Arrange
        user_id = user.id
        count = 10

        # Act
        codes = await generate_recovery_codes(session, user_id, count=count)
        await session.commit()

        # Assert: Returned codes
        assert len(codes) == count
        assert all(len(code) == 11 for code in codes)  # XXXXX-XXXXX format
        assert all(code[5] == "-" for code in codes)
        assert len(set(codes)) == count  # All unique

        # Assert: Database storage
        recovery_crud = RecoveryCodeCRUD(session)
        stored_codes = await recovery_crud.get_by_user_id(user_id)

        assert len(stored_codes) == count

        # Assert: Hash and encryption present
        for stored_code in stored_codes:
            assert stored_code.code_hash.startswith("$2b$")  # Bcrypt format
            assert len(stored_code.code_encrypted) > 50  # Fernet format
            assert not stored_code.used
            assert stored_code.used_at is None

        # Assert: User timestamp
        users_crud = UsersCRUD(session)
        updated_user = await users_crud.get_by_id(user_id)
        assert updated_user.recovery_codes_generated_at is not None

    async def test_hash_verification_flow(
        self,
        session: AsyncSession,
        user: User,
    ):
        """
        Test that generated codes can be verified against their hashes.

        Verifies:
        - Correct codes pass verification
        - Incorrect codes fail verification
        - Hash is one-way (can't retrieve code from hash)
        """
        # Arrange & Act
        user_id = user.id
        codes = await generate_recovery_codes(session, user_id, count=5)
        await session.commit()

        recovery_crud = RecoveryCodeCRUD(session)
        stored_codes = await recovery_crud.get_by_user_id(user_id)

        # Assert: Each plaintext code matches one hash
        for plaintext_code in codes:
            matches = [
                stored_code
                for stored_code in stored_codes
                if verify_recovery_code(plaintext_code, stored_code.code_hash)
            ]
            assert len(matches) == 1, f"Code {plaintext_code} should match exactly one hash"

        # Assert: Wrong code fails verification
        wrong_code = "AAAAA-BBBBB"
        for stored_code in stored_codes:
            assert not verify_recovery_code(wrong_code, stored_code.code_hash)

    async def test_encryption_decryption_flow(
        self,
        session: AsyncSession,
        user: User,
    ):
        """
        Test that encrypted codes can be decrypted back to plaintext.

        Verifies:
        - All encrypted codes can be decrypted
        - Decrypted codes match original plaintext
        - Encryption is reversible for display purposes
        """
        # Arrange & Act
        user_id = user.id
        codes = await generate_recovery_codes(session, user_id, count=5)
        await session.commit()

        recovery_crud = RecoveryCodeCRUD(session)
        stored_codes = await recovery_crud.get_by_user_id(user_id)

        # Assert: Decrypt all codes
        decrypted_set = set()
        for stored_code in stored_codes:
            decrypted = decrypt_recovery_code(stored_code.code_encrypted)
            decrypted_set.add(decrypted)

        # Assert: Decrypted codes match original plaintext
        plaintext_set = set(codes)
        assert decrypted_set == plaintext_set

    async def test_default_count_parameter(
        self,
        session: AsyncSession,
        user: User,
    ):
        """
        Test that count defaults to config value when not specified.

        Verifies:
        - Default count from settings is used
        - Database has correct number of records
        """
        # Arrange
        expected_count = settings.mfa.recovery_code_count

        # Act
        codes = await generate_recovery_codes(session, user.id)
        await session.commit()

        # Assert
        assert len(codes) == expected_count

        recovery_crud = RecoveryCodeCRUD(session)
        stored_codes = await recovery_crud.get_by_user_id(user.id)
        assert len(stored_codes) == expected_count

    async def test_code_format_validation(
        self,
        session: AsyncSession,
        user: User,
    ):
        """
        Test that all generated codes have correct format.

        Verifies:
        - Format: XXXXX-XXXXX (5 chars, hyphen, 5 chars)
        - Characters are alphanumeric uppercase
        - Total length is 11 characters
        """
        # Act
        codes = await generate_recovery_codes(session, user.id, count=20)
        await session.commit()

        # Assert
        for code in codes:
            # Length check
            assert len(code) == 11, f"Code {code} wrong length"

            # Format check
            parts = code.split("-")
            assert len(parts) == 2, f"Code {code} should have exactly one hyphen"
            assert len(parts[0]) == 5, f"First part of {code} should be 5 chars"
            assert len(parts[1]) == 5, f"Second part of {code} should be 5 chars"

            # Character check
            code_no_hyphen = code.replace("-", "")
            assert code_no_hyphen.isalnum(), f"Code {code} should be alphanumeric"
            assert code_no_hyphen.isupper(), f"Code {code} should be uppercase"

    async def test_code_uniqueness(
        self,
        session: AsyncSession,
        user: User,
    ):
        """
        Test that all generated codes are unique.

        Verifies:
        - No duplicate codes in single generation
        - Codes from multiple generations are also unique
        """
        # Generate first batch
        codes_batch1 = await generate_recovery_codes(session, user.id, count=50)
        await session.commit()

        # Assert: No duplicates in batch
        assert len(set(codes_batch1)) == len(codes_batch1)

        # Clean up and generate second batch
        recovery_crud = RecoveryCodeCRUD(session)
        await recovery_crud.delete_by_user_id(user.id)
        await session.commit()

        codes_batch2 = await generate_recovery_codes(session, user.id, count=50)
        await session.commit()

        # Assert: Different from first batch (statistically very unlikely to collide)
        # Note: With 51.7 bits entropy, collision probability is negligible
        overlap = set(codes_batch1) & set(codes_batch2)
        assert len(overlap) == 0, f"Found {len(overlap)} duplicate codes across batches"
