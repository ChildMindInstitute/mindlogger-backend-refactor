with pending_invitations as (
	select i.id
	from invitations i
	join user_applet_accesses uaa on
		1 = 1
		and uaa.applet_id = i.applet_id
		and uaa.meta->>'secretUserId' = i.meta->>'secret_user_id'
	where
		1 = 1
		and i."role" = 'respondent'
		and uaa."role" = 'respondent'
		and i.status = 'pending'
		and uaa.is_deleted is not true
)
delete from invitations using pending_invitations
where invitations.id = pending_invitations.id