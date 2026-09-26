# Local Compiler Explorer + VS Code Shortcut Setup

This setup gives you the following workflow:

```text
VS Code
   │
   │ current C/C++ file
   │
   │ Ctrl+Alt+G [keyboard shortcut]
   ▼
VS Code task
   │
   ▼
~/scripts/ce-open.py
   │
   ├── reads current source file
   ├── reads compile_commands.json
   ├── extracts compiler flags
   └── sends state to local Compiler Explorer
              │
              ▼
      reusable Compiler Explorer tab
```

The main goal is to inspect the currently opened C++ file in your local Compiler Explorer without copying and pasting code.

---

# 1. Install Compiler Explorer locally and start 

```bash

git clone https://github.com/compiler-explorer/compiler-explorer.git
```

```bash
make
```
By default, local Compiler Explorer should be available at:

```text
http://localhost:10240
```

---

# 2. Verify your compilers

Check which GCC and Clang versions are installed:

```bash
g++ --version
clang++ --version
```

Also check their locations:

```bash
which g++
which clang++
```

For example:

```text
/usr/bin/g++
/usr/bin/clang++
```

---

# 3. Configure local GCC and Clang in Compiler Explorer

```bash
compiler-explorer/etc/scripts/ce-properties-wizard/run.sh <compiler-location>
```

Restart local CE & Verify the available compilers:

```bash
curl -s http://localhost:10240/api/compilers/c++
```

---

# 4. Generate `compile_commands.json`

Your project needs a compilation database so the helper script knows the real flags used by your build.

---

# 5. Retrieve the Compiler Explorer helper scripts

Retrieve `ce-open.py` and `ce-tab.py`

Configure the compiler ID in `ce-open.py`. This should be the name field from the previous step's GET curl request.
```python
COMPILER_ID = os.environ.get(
    "CE_COMPILER_ID",
    "clang22",
)
```

---

# 6. Start the reusable tab relay script 

Run:

```bash
~/scripts/ce-tab.py
```

You should see:

```text
Compiler Explorer relay running:
http://127.0.0.1:8123
```

Open:

```text
http://127.0.0.1:8123
```

Click:

```text
Open Compiler Explorer
```

This opens one Compiler Explorer tab.

Keep both tabs open:

```text
Compiler Explorer Relay

Compiler Explorer
```

The second tab will be reused every time you invoke the VS Code shortcut.

---


# 7. Configure the VS Code task

Inside your project create:

```text
.vscode/tasks.json
```

```json
{
    "version": "2.0.0",

    "tasks": [
        {
            "label": "Compiler Explorer: Current File",

            "type": "process",

            "command": "${env:HOME}/scripts/ce-open.py",

            "args": [
                "${file}",
                "${workspaceFolder}/build/compile_commands.json"
            ],

            "problemMatcher": [],

            "presentation": {
                "reveal": "silent",
                "panel": "shared",
                "clear": true
            }
        }
    ]
}
```
The `tasks.command` value needs to be updated to the location of your ce-open.py script.   

---

# 8. Add the keyboard shortcut [optional]

Open:

```text
Preferences: Open Keyboard Shortcuts (JSON)
```

Add:

```json
[
    {
        "key": "ctrl+alt+g",
        "command": "workbench.action.tasks.runTask",
        "args": "Compiler Explorer: Current File"
    }
]
```

Now:

```text
Ctrl+Alt+G
```

runs Compiler Explorer for the currently opened file.

---
