from apps.authentication.services import AuthenticationService
from apps.migrate.answers.crud import MigrateUsersMCRUD
from apps.migrate.answers.settings import LegacyDeletedRespondent
from apps.users import UserSchema
from apps.users.services.user import UserService


class UserMigrateService(UserService):
    async def create_legacy_deleted_respondent(self):
        crud = MigrateUsersMCRUD(self.session)
        legacy_deleted_respondent = await crud.get_legacy_deleted_respondent()
        if legacy_deleted_respondent:
            return legacy_deleted_respondent
        else:
            legacy_deleted_respondent_settings = LegacyDeletedRespondent()
            legacy_deleted_respondent_schema = UserSchema(
                email=legacy_deleted_respondent_settings.email,
                first_name=legacy_deleted_respondent_settings.first_name,
                last_name=legacy_deleted_respondent_settings.last_name,
                hashed_password=AuthenticationService(
                    self.session
                ).get_password_hash(
                    legacy_deleted_respondent_settings.password
                ),
                is_legacy_deleted_respondent=True,
            )
            await crud.save(legacy_deleted_respondent_schema)
