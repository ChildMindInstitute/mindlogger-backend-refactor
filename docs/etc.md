
### Update gender_screen and age_screen activity items strings to greek for an applet

```bash
python src/cli.py patch exec M2-8568 -a <applet_id>
```

> [!NOTE]
> You can use environment variables to overwrite default values.
>
> | Environment variable | Text string |
> | - | - |
> | `AGE_SCREEN_QUESTION_TRANSLATION` | Question text for the Age screen |
> | `GENDER_SCREEN_QUESTION_TRANSLATION` | Question text for the Gender screen |
> | `GENDER_SCREEN_RESPONSE_MALE_TRANSLATION` | "Male" response text |
> | `GENDER_SCREEN_RESPONSE_FEMALE_TRANSLATION` | "Female" response text |

### Library cleanup

You can use the following command to remove entries from the `library` table (as the Library feature lacks a delete endpoint):

```bash
python src/cli.py patch exec M2-9015 --applets '{"<applet_id>": "<applet_name>", ...}'
```
