# ci-check-test-locations.sh
stray=$(find . -path "./.venv" -prune -o -name "test_*.py" -not -path "./tests/unit/*" -not -path "./tests/integration/*" -not -path "./tests/legacy/*" -print)
if [ -n "$stray" ]; then
    echo "Test files found outside tests/unit, tests/integration, tests/legacy:"
    echo "$stray"
    exit 1
fi