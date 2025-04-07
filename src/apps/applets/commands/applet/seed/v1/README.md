# Applet Seed Command v1

## Description

A command to seed the applet database with initial data from a yaml config file. This command is intended for
development and testing purposes only.

```
Usage: python src/cli.py applet seed <PATH_TO_CONFIG>
  
 Arguments:
  <PATH_TO_CONFIG>     Path to the config file [default: None] [required]

Options:
  --help            Show this help message and exit
  
Example:
  python src/cli.py applet seed /path/to/config.yaml
```

There are several things that are not supported by this seed command. They are:
- Activity flows
- Subscales
- Activity report configurations (report server configurations **are** supported)

## Configuration File

The configuration file is a YAML file that contains the initial data for the applet database. The file should contain
the following fields (required fields are marked with an asterisk):

- `*version`: The string "1.0"
- `users`: A list of [User](#user-object) objects
- `applets`: A list of [Applet](#applet-object) objects

### User Object

The details of an existing user, or a new user to be created. If these are the details of an existing user, they must
match exactly. No updates will be made to an existing user.

It is recommended to have the applet owner be an existing user, so that their encryption object can be reused in
the [Applet Object](#applet-object) below.

- `*id`: The UUID id of the user
- `created_at`: The date the user was created
- `*email`: The email address of the user
- `*first_name`: The first name of the user
- `*last_name`: The last name of the user
- `*password`: The password of the user in plain text

## Applet Object

The details of a new applet to be created. The id and display_name must not match any existing applets, otherwise an
error will be raised.

- `*id`: The UUID id of the applet
- `*encryption`: The encryption object of the applet. This should be taken from an existing applet, otherwise the applet
  password will not work.
- `*display_name`: The display name of the applet.
- `subjects`: A list of [Subject](#subject-object) objects. At least the applet owner must be specified.
- `activities`: A list of [Activity](#activity-object) objects. There must be at least one activity defined.
- `description`: A text description of the applet (defaults to an empty string if not provided).
- `created_at`: A timestamp indicating when the applet was created.
- `report_server`: (Optional) A [Report Server](#report-server-object) configuration object for report generation.

### Applet Encryption Object

The encryption object provides the security details for the applet and includes the following required fields:
- `*account_id`: The UUID of the applet owner.
- `*base`: The generator base as a string.
- `*prime`: A string representing a large prime number.
- `*public_key`: The public key used for encryption.

This value will likely be taken from an existing applet.

### Activity Object

Activities represent individual tasks or modules within an applet. Each activity object must include:
- `*id`: The UUID id of the activity.
- `*name`: The name of the activity.
- `events`: A list of [Event](#event-configurations) objects (at least one event is required).
- `description`: A description of the activity (defaults to an empty string).
- `auto_assign`: A boolean indicating whether the activity is automatically assigned to all participants (defaults to true).
- `created_at`: A timestamp for when the activity was created.
- `is_hidden`: A boolean flag that indicates if the activity is hidden (defaults to false).

### Event Configurations

Events schedule the availability periods of an activity. Every event object includes the following common properties:
- `*id`: A unique UUID for the event.
- `*version`: A version string in the format `YYYYMMdd-n` (e.g., `20250301-1`).
- `*periodicity`: A string indicating the event type. Allowed values include `ALWAYS`, `DAILY`, `ONCE`, `WEEKLY`, `WEEKDAYS`, or `MONTHLY`.
- `*created_at`: A timestamp indicating when the event was created.
- `*start_time`: The start time of the event.
- `*end_time`: The end time of the event.
- `is_deleted`: (Optional) A flag to mark the event as deleted (defaults to false).
- `notifications`: (Optional) A list of [Notification](#notification-configurations) objects.
- `reminder`: (Optional) A [Reminder](#reminder-configuration) object.
- `user_id`: (Optional) A UUID for a user-specific event identifier.

Depending on the type of event, additional fields are required:

- **AlwaysAvailableEventConfig**: May include `one_time_completion` (a boolean to indicate if the event can only be completed once per day).
- All but **AlwaysAvailableEventConfig**: May include `access_before_start_time` (a boolean to allow access before the event's start time on a given day).
- **DailyEventConfig** and **WeekdaysEventConfig**: Require `start_date` and `end_date` to define the event's date range.
- **OnceEventConfig**: Requires `selected_date` to specify the single occurrence date.
- **MonthlyEventConfig** and **WeeklyEventConfig**: Require both a date range (`start_date` and `end_date`) and a `selected_date` for a specific recurring instance.

`start_date`, `end_date`, and `selected_date` are timestamps in the format `YYYY-MM-DDTHH:MM:SSZ` (e.g., `2023-10-01T00:00:00Z`).

### Notification Configurations

Notifications alert participants about events and come in two variants:

#### Fixed Notification

A notification that is sent at a specific time. It includes:

- `*trigger_type`: Must be `"fixed"`.
- `at_time`: (Optional) The specific time when the notification should be sent.

#### Random Notification

A notification that is sent at a random time within a specified window. It includes:

- `*trigger_type`: Must be `"random"`.
- `from_time`: The start time for the notification window.
- `to_time`: The end time for the notification window.

### Reminder Configuration

The reminder object ensures that users are notified if an activity is not completed after a certain amount of time. It includes:
- `*activity_incomplete`: An integer specifying how many consecutive days the activity must remain incomplete before triggering the reminder.
- `*reminder_time`: The time at which the reminder should be sent.

### Report Server Object

For applets that generate reports, the report server configuration includes:
- `*ip_address`: The URI of the report server.
- `*public_key`: The RSA public key for secure communication.
- `*email_body`: The content of the email to be sent with the report.
- `include_case_id`: (Optional) A boolean indicating whether to include a case ID in the report (defaults to false).
- `include_user_id`: (Optional) A boolean indicating whether to include a user ID in the report (defaults to false).
- `recipients`: (Optional) A list of email addresses that will receive the report (defaults to an empty array).

### Subject Object

Subjects represent the individual participants within an applet. Each subject object must include:
- `*id`: The UUID id of the subject.
- `*secret_user_id`: A unique secret identifier for the subject (must be unique within the applet).
- `*first_name`: The subject's first name (minimum one character).
- `*last_name`: The subject's last name (minimum one character).
- `*roles`: An array of strings indicating the roles assigned to the subject. This array must include `"respondent"` and may also contain `super_admin`, `owner`, `manager`, `coordinator`, `editor`, or `reviewer`.

Optional fields include:
- `created_at`: The date the subject was created.
- `email`: The email address used for the invitation.
- `nickname`: An optional nickname.
- `reviewer_subjects`: An array of UUIDs representing subjects that this reviewer will review. Required for reviewers.
- `tag`: An optional tag with allowed values: Child, Parent, Teacher, or Team.
- `user_id`: An optional UUID linking the subject to a full user account or team member. This user must be defined in the `users` section of the configuration file.

## Conclusion

This configuration schema provides a comprehensive framework for seeding the applet database. By clearly defining users, applets (with their encryption, subjects, and activities), events (with notifications and reminders), and report server settings, the schema ensures consistency and reliability across development and testing environments. Use this guide to understand the required structure and fields when creating your YAML configuration file.
