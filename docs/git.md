## Scripts

### Using pre-commit hooks

It is a good practice to use Git hooks to provide better commits.

For increased security during development, install `git-secrets` to scan code for aws keys.

Please use this link for that: https://github.com/awslabs/git-secrets#installing-git-secrets

`.pre-commit-config.yaml` is placed in the root of the repository.

👉 Once you have installed `git-secrets` and `pre-commit` simply run the following command.

```bash
make aws-scan
```

👉 Then all your staged changes will be checked via git hooks on every `git commit`

