from typing import Literal

from sqlalchemy import Column, asc, desc

from .domain.base import to_camelcase

__all__ = ["Ordering"]

from sqlalchemy.orm import InstrumentedAttribute

OrderingDirection = Literal["+", "-"]

# Record limit for ordering by encrypted fields to minimize performance impact
ENCRYPTED_ORDERING_LIMIT = 300


class Ordering:
    """
    Generates clauses for SQL ordering, with support for conditional ordering by encrypted fields.

    For unencrypted fields, define them directly as class attributes as schema columns or
    ordering clauses.

    For encrypted fields, add them to the encrypted_fields dictionary as ordering clauses
    (including decryption logic).

    Clauses returned by get_clauses will only include requested encrypted fields only if record
    count is below ENCRYPTED_ORDERING_LIMIT.

    Example:

    ```
        class BasicOrdering(Ordering):
            id = Schema.id
            date = Schema.created_at

        ordering = BasicOrdering()
        query.order_by(*ordering.get_clauses('-id', 'date'))
        # Will give result as SQL:
        #   select * from schema order by id desc, created_at asc


        class EncryptedOrdering(Ordering):
            id = Schema.id
            date = Schema.created_at

            # encrypted_fields is optional, only needed if one or more fields are encrypted
            encrypted_fields = {
                "email": Ordering.Clause(func.decrypt_internal(UserSchema.email, get_key())),
            }

        ordering = EncryptedOrdering()
        count = (await session.execute(
            select(count()).select_from(query.with_only_columns(Schema.id).subquery())
        )).scalar()
        query.order_by(*ordering.get_clauses_encrypted("email", "-date", count=count))
        # If count < ENCRYPTED_ORDERING_LIMIT, will give result as SQL:
        #   select * from schema order by decrypt_internal(email, …) asc, created_at desc
        # and EncryptedOrdering().get_ordering_fields(count) will return ["id", "date", "email"]
        #
        # Else if count >= ENCRYPTED_ORDERING_LIMIT, will give result as SQL:
        #   select * from schema order by created_at desc
        # and EncryptedOrdering().get_ordering_fields(count) will return ["id", "date"]
    ```
    """

    class Clause:
        """
        Wrapper for complex ordering
        """

        def __init__(self, clause):
            self.clause = clause

    fields: dict[str, InstrumentedAttribute | Column | Clause] = dict()
    encrypted_fields: dict[str, InstrumentedAttribute | Column | Clause] = dict()

    actions = {
        "+": asc,
        "-": desc,
    }

    def __init__(self):
        self.fields = dict()
        for key, val in self.__class__.__dict__.items():
            _val = None
            if isinstance(val, (InstrumentedAttribute, Column)):
                _val = val
            elif isinstance(val, Ordering.Clause):
                _val = val.clause
            if _val is not None:
                self.fields[key] = _val

        for key, val in self.encrypted_fields.items():
            _val = None
            if isinstance(val, (InstrumentedAttribute, Column)):
                _val = val
            elif isinstance(val, Ordering.Clause):
                _val = val.clause
            if _val is not None:
                self.encrypted_fields[key] = _val

    def get_clauses(self, *args: str, count: int = 0):
        """
        Returns SQL clauses suitable for Query.order_by based on provided "+field"-style args,
        including any requested encrypted fields only if provided record count is below
        ENCRYPTED_ORDERING_LIMIT.
        """
        clauses: list[str] = []
        for value in args:
            parsed_field = self._parse_ordered_field(value)
            if parsed_field is None:
                continue

            direction, field = parsed_field
            clause = None
            if field in self.fields:
                clause = self._prepare_sql_clause((direction, self.fields[field]))
            elif field in self.encrypted_fields and count < ENCRYPTED_ORDERING_LIMIT:
                clause = self._prepare_sql_clause((direction, self.encrypted_fields[field]))
            else:
                continue

            if clause is not None:
                clauses.append(clause)
        return clauses

    def get_ordering_fields(self, count: int = 0):
        """
        Returns list of fields that this Ordering class supports for sorting, which includes
        encrypted fields only if provided record count is below ENCRYPTED_ORDERING_LIMIT.

        Returns field names in camelCase suitable for API output.
        """
        fields = [*self.fields.keys()]
        include_encrypted_fields = bool(self.encrypted_fields) and count < ENCRYPTED_ORDERING_LIMIT
        if include_encrypted_fields:
            fields += self.encrypted_fields.keys()
        return list(to_camelcase(word) for word in fields)

    def _parse_ordered_field(self, value: str):
        if not value:
            return None
        direction, field = value[0], value[1:]
        if direction != "-":
            field = value
            direction = "+"
        field = field.lstrip("+")
        return (direction, field)

    def _prepare_sql_clause(self, value: tuple[OrderingDirection, InstrumentedAttribute | Column | Clause]):
        direction, expression = value

        return self.actions[direction](expression)
