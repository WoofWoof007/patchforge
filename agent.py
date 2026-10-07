import os
import re
import subprocess
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    base_url="https://api.tokenfactory.us-central1.nebius.com/v1/",
    api_key=os.environ["NEBIUS_API_KEY"],
)
MODEL = os.environ["NEBIUS_MODEL"]


def ask(prompt):
    reply = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return reply.choices[0].message.content


def extract_code(text):
    match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    return match.group(1) if match else text


def run_tests(repo):
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=repo, capture_output=True, text=True, timeout=60,
    )
    return result.returncode == 0, result.stdout + result.stderr


def main(repo, source_file):
    source_path = os.path.join(repo, source_file)
    source = open(source_path).read()
    issue = open(os.path.join(repo, "issue.txt")).read()

    # Step 1: write a test that reproduces the bug
    print("1. Writing a failing test...")
    test_code = extract_code(ask(
        f"Bug report:\n{issue}\n\nCode in {source_file}:\n{source}\n\n"
        f"Write a pytest file with ONE test that fails because of this bug. "
        f"Import from the module '{source_file[:-3]}'. "
        f"Return only the code in a python code block."
    ))
    repro_path = os.path.join(repo, "test_repro.py")
    open(repro_path, "w").write(test_code)

    passed, output = run_tests(repo)
    if passed:
        print("The new test passed, so the bug was NOT reproduced. Stopping.")
        return
    print("   Test fails as expected. Bug confirmed.")

    # Step 2: try to fix, up to 3 attempts
    last_output = output
    for attempt in range(1, 4):
        print(f"2. Fix attempt {attempt}...")
        fixed = extract_code(ask(
            f"Bug report:\n{issue}\n\nCurrent code in {source_file}:\n{source}\n\n"
            f"Test output:\n{last_output}\n\n"
            f"Return the COMPLETE fixed contents of {source_file} "
            f"in a python code block. Change as little as possible."
        ))
        open(source_path, "w").write(fixed)

        passed, last_output = run_tests(repo)
        if passed:
            print("3. All tests pass. Fix verified!")
            print("\n--- Fixed code ---\n" + fixed)
            return
        print("   Still failing, trying again...")

    open(source_path, "w").write(source)  # restore original
    print("Could not fix it in 3 attempts. Original code restored.")


if __name__ == "__main__":
    main("demo_repos/cart_bug", "cart.py")