#!/bin/bash
cd /pentbox
echo "Starting PentBox Honeypot on port 23..."
find . -name "pentbox.rb" | head -1 | xargs ./ <<EOF || find . -name "pentbox.rb" | head -1 | xargs ./pentbox-1.8/
2
3
23
LLM LeakGuard Enterprise Honeypot - Intrusion Logged!
EOF
tail -f /dev/null