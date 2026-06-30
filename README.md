# kickstarter-wechat-post has moved

This repository has been merged into the unified content-creation experience repository:

https://github.com/ositoakabear/content-production-sop

The maintained skill now lives here:

```text
content-production-sop/
  skills/cursor/kickstarter-wechat-post/
```

The Kickstarter product playbook lives here:

```text
content-production-sop/
  playbooks/kickstarter/
```

## New install command

macOS/Linux:

```bash
git clone https://github.com/ositoakabear/content-production-sop.git /tmp/content-playbook \
  && mkdir -p ~/.cursor/skills \
  && cp -r /tmp/content-playbook/skills/cursor/kickstarter-wechat-post ~/.cursor/skills/
```

Windows PowerShell:

```powershell
git clone https://github.com/ositoakabear/content-production-sop.git $env:TEMP\content-playbook
New-Item -ItemType Directory -Force "$HOME\.cursor\skills" | Out-Null
Copy-Item -Recurse "$env:TEMP\content-playbook\skills\cursor\kickstarter-wechat-post" "$HOME\.cursor\skills\"
```

## Status of this repository

The files in this repository are kept as a historical standalone copy. Future updates should go to:

- `content-production-sop/skills/cursor/kickstarter-wechat-post/`
- `content-production-sop/playbooks/kickstarter/`
- `content-production-sop/docs/`
- `content-production-sop/scripts/wechat/`
