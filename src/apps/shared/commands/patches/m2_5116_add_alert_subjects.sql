update alerts
set subject_id = (
	select id
	from subjects
	where
		applet_id = alerts.applet_id
		and user_id = alerts.respondent_id
)
where
	respondent_id is not null
