update
	subjects sj
set
	tag = 'Team'
from
	user_applet_accesses uaa
where
	sj.user_id = uaa.user_id
	and uaa.role != 'respondent';