#! /bin/bash

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cat << EOF > hey
#! /bin/bash
source .venv/bin/activate
hey.py $*
EOF
chmod +x hey
ln -sf $(pwd)/hey ~/.local/bin/hey
echo "Created 'hey' and symlinked to ~/.local/bin/hey"
