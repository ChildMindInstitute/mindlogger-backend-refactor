insert into subjects (
	id,
	applet_id,
	user_id,
	email,
	first_name,
	last_name,
	nickname,
	secret_user_id,
	creator_id,
	created_at,
	updated_at
)
select
	(md5(uaa.applet_id::text || uaa.user_id::text))::uuid as id,
	uaa.applet_id,
	uaa.user_id,
	users.email_encrypted as email,
	users.first_name,
	users.last_name,
	uaa.nickname,
	uaa.meta->>'secretUserId' as secret_user_id,
	uaa.owner_id as creator_id,
	uaa.created_at,
	uaa.updated_at
from
	user_applet_accesses uaa
	join users on users.id = uaa.user_id
where uaa.role = 'respondent';
