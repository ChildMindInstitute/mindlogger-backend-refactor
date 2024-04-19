update invitations i
    set user_id = u.id
from users u
where u.email_encrypted = i.email
    and i.status != 'pending'
    and i.user_id is null
    and u.email_encrypted is not null
;
