# Error Codes

Backend error responses include an `error_code` field for frontend localization.

## Response Format

```json
{
  "result": [
    {
      "message": "Invalid TOTP code",
      "type": "ACCESS_DENIED",
      "path": []
    }
  ],
  "error_code": "AUTH.MFA.INVALID_TOTP_CODE"
}
```

- `result[].message` - English error message (backwards compatibility)
- `error_code` - Unique code for frontend translation lookup

## Error Code Format

Pattern: `DOMAIN.CATEGORY.SPECIFIC_ERROR`

Example: `AUTH.MFA.INVALID_TOTP_CODE`

## MFA Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `AUTH.MFA.INVALID_TOTP_CODE` | 401 | Invalid or incorrect TOTP code |
| `AUTH.MFA.SESSION_NOT_FOUND` | 401 | MFA session not found or expired |
| `AUTH.MFA.TOO_MANY_ATTEMPTS` | 429 | Max attempts (5) exceeded for session |
| `AUTH.MFA.GLOBAL_LOCKOUT` | 429 | Global lockout (10+ failed attempts) |
| `AUTH.MFA.TOKEN_EXPIRED` | 401 | MFA JWT token expired (5 min timeout) |
| `AUTH.MFA.TOKEN_INVALID` | 401 | MFA JWT token invalid or corrupted |
| `AUTH.MFA.TOKEN_MALFORMED` | 401 | MFA JWT token format incorrect |

## Auth Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `AUTH.AUTHENTICATION_ERROR` | 401 | Generic authentication failure |
| `AUTH.INVALID_CREDENTIALS` | 401 | Invalid email or password |
| `AUTH.INVALID_REFRESH_TOKEN` | 400 | Refresh token invalid or expired |
| `AUTH.PERMISSIONS_ERROR` | 403 | Insufficient permissions |
| `AUTH.EMAIL_DOES_NOT_EXIST` | 403 | Email not associated with account |

## Frontend Usage

```typescript
try {
  await api.verifyMFA(code);
} catch (error) {
  const code = error.response.data.error_code;
  const message = t(`errors.${code}`) || error.response.data.result[0].message;
  showError(message);
}
```

## Adding New Codes

1. Add to `src/apps/authentication/constants.py`:
   ```python
   NEW_ERROR = "AUTH.CATEGORY.NEW_ERROR"
   ```

2. Add to error class in `src/apps/authentication/errors.py`:
   ```python
   class NewError(AuthenticationError):
       message = _("Error message")
       error_code = AuthErrorCode.NEW_ERROR
   ```

3. Update frontend translation files

