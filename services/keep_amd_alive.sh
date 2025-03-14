[Unit]
Description=Awaiting User Agent Service
After=network.target

[Service]
Type=simple
ExecStart=/bin/bash -c 'log_file="/root/answering-machine-detection/log/log-01-$(uuidgen).txt" && source /root/.bashrc && /root/venv/bin/python /root/answering-machine-detection/src/user_agent.py --domain "127.0.0.1" --src-user "8501" --src-pass "pass8501" --always > "$log_file" 2>&1'
Restart=always
RestartSec=3
Environment="PATH=/usr/local/bin:/usr/bin"
TimeoutStartSec=infinity
StandardOutput=journal
RemainAfterExit=true
User=root

[Install]
WantedBy=multi-user.target
