from typing import List

from pydantic import BaseModel


class Logs(BaseModel):
    cycle_days: int = 14
    access: str = ""

    def get_access_emails(self) -> List[str]:
        emails_raw = list(filter(lambda s: s, self.access.split(",")))
        emails = []
        for email in emails_raw:
            if email:
                emails.append(email.lower().strip())
        return emails
