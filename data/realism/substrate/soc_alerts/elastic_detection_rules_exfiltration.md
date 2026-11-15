---
source: https://github.com/elastic/detection-rules (three rules, paths below)
retrieved: 2026-11-15
license: Elastic License 2.0
---

## rules/cross-platform/exfiltration_potential_curl_data_exfiltration.toml
```toml
[metadata]
creation_date = "2025/04/29"
integration = ["endpoint", "windows", "system", "sentinel_one_cloud_funnel", "crowdstrike", "auditd_manager"]
maturity = "production"
updated_date = "2026/10/06"

[rule]
author = ["Elastic"]
description = """
Detects the use of curl to upload files to an internet server. Threat actors often will collect and exfiltrate data on a 
system to their C2 server for review. Many threat actors have been observed using curl to upload the collected data. Use
of curl in this way, while not inherently malicious, should be considered highly abnormal and suspicious activity.
"""
from = "now-9m"
index = [
    "logs-crowdstrike.fdr*",
    "logs-endpoint.events.process-*",
    "logs-sentinel_one_cloud_funnel.*",
    "logs-system.security*",
    "logs-windows.forwarded*",
    "logs-windows.sysmon_operational-*",
    "winlogbeat-*",
    "auditbeat-*",
    "logs-auditd_manager.auditd-*"
]
language = "eql"
license = "Elastic License v2"
name = "Potential Data Exfiltration Through Curl"
note = """ ## Triage and analysis

> **Disclaimer**:
> This investigation guide was created using generative AI technology and has been reviewed to improve its accuracy and relevance. While every effort has been made to ensure its quality, we recommend validating the content and adapting it to suit your specific environment and operational needs.

### Investigating Potential Data Exfiltration Through Curl

Curl is a command-line tool used for transferring data with URLs, commonly employed for legitimate data exchange tasks. However, adversaries can exploit curl to exfiltrate sensitive data by uploading compressed files to remote servers. The detection rule identifies suspicious curl usage by monitoring for specific command patterns and arguments indicative of data uploads, flagging abnormal activities for further investigation.

### Possible investigation steps

- Review the process command line to confirm the presence of suspicious arguments such as "-F", "-T", "-d", or "--data*" and check for any compressed file extensions like .zip, .gz, or .tgz being uploaded to an external server.
- Investigate the parent process of the curl command to understand the context in which curl was executed, including the parent executable and its purpose.
- Examine network logs to identify the destination IP address or domain to which the data was being uploaded, and assess whether it is a known or suspicious entity.
- Check for any recent file creation or modification events on the host that match the compressed file types mentioned in the query, which could indicate data collection prior to exfiltration.
- Correlate this event with other security alerts or logs from the same host to identify any patterns of behavior that might suggest a broader compromise or data exfiltration attempt.

### False positive analysis

- Legitimate data transfers using curl for system backups or data synchronization can trigger the rule. To manage this, identify and whitelist specific processes or scripts that are known to perform these tasks regularly.
- Automated system updates or software installations that use curl to download and upload data might be flagged. Exclude these processes by verifying their source and adding them to an exception list if they are from trusted vendors.
- Internal data transfers within a secure network that use curl for efficiency can be mistaken for exfiltration. Monitor the destination IP addresses and exclude those that are internal or known safe endpoints.
- Developers or system administrators using curl for testing or development purposes may inadvertently trigger the rule. Educate these users on the potential alerts and establish a process for them to notify security teams of their activities to prevent unnecessary investigations.
- Scheduled tasks or cron jobs that use curl for routine data uploads should be reviewed and, if deemed safe, added to an exception list to avoid repeated false positives.

### Response and remediation

- Immediately isolate the affected system from the network to prevent further data exfiltration and contain the threat.
- Terminate any suspicious curl processes identified by the detection rule to stop ongoing data transfers.
- Conduct a forensic analysis of the affected system to identify any additional malicious activities or compromised data.
- Change credentials and access keys that may have been exposed or used during the incident to prevent unauthorized access.
- Notify the security operations team and relevant stakeholders about the incident for awareness and further action.
- Review and update firewall and network security rules to block unauthorized outbound traffic, especially to suspicious or unknown external servers.
- Implement enhanced monitoring and logging for curl usage and similar data transfer tools to detect and respond to future exfiltration attempts promptly.
"""
references = [
  "https://everything.curl.dev/usingcurl/uploads",
  "https://cloud.google.com/blog/topics/threat-intelligence/disrupting-gridtide-global-espionage-campaign?hl=en"
]
risk_score = 47
rule_id = "be70614d-4295-473c-a953-582aef41c865"
setup = """## Setup

This rule requires data coming in from Elastic Defend.

### Elastic Defend Integration Setup
Elastic Defend is integrated into the Elastic Agent using Fleet. Upon configuration, the integration allows the Elastic Agent to monitor events on your host and send data to the Elastic Security app.

#### Prerequisite Requirements:
- Fleet is required for Elastic Defend.
- To configure Fleet Server refer to the [documentation](https://www.elastic.co/guide/en/fleet/current/fleet-server.html).

#### The following steps should be executed in order to add the Elastic Defend integration on a Linux System:
- Go to the Kibana home page and click "Add integrations".
- In the query bar, search for "Elastic Defend" and select the integration to see more details about it.
- Click "Add Elastic Defend".
- Configure the integration name and optionally add a description.
- Select the type of environment you want to protect, either "Traditional Endpoints" or "Cloud Workloads".
- Select a configuration preset. Each preset comes with different default settings for Elastic Agent, you can further customize these later by configuring the Elastic Defend integration policy. [Helper guide](https://www.elastic.co/guide/en/security/current/configure-endpoint-integration-policy.html).
- We suggest selecting "Complete EDR (Endpoint Detection and Response)" as a configuration setting, that provides "All events; all preventions"
- Enter a name for the agent policy in "New agent policy name". If other agent policies already exist, you can click the "Existing hosts" tab and select an existing policy instead.
For more details on Elastic Agent configuration settings, refer to the [helper guide](https://www.elastic.co/guide/en/fleet/8.10/agent-policy.html).
- Click "Save and Continue".
- To complete the integration, select "Add Elastic Agent to your hosts" and continue to the next section to install the Elastic Agent on your hosts.
For more details on Elastic Defend refer to the [helper guide](https://www.elastic.co/guide/en/security/current/install-endpoint.html).
"""
severity = "medium"
tags = [
    "Domain: Endpoint",
    "OS: Linux",
    "OS: Windows",
    "OS: macOS",
    "Use Case: Threat Detection",
    "Tactic: Exfiltration",
    "Resources: Investigation Guide",
    "Data Source: Elastic Defend",
    "Data Source: Crowdstrike",
    "Data Source: SentinelOne",
    "Data Source: Sysmon",
    "Data Source: Auditd Manager",
    "Data Source: Windows Security Event Logs",
    "Noise: High",
    "Performance: Normal",
    "Profile: Aggressive",
    "Threat: Download Tool Abuse",
    "Rule Type: Event Correlation (EQL)",
    "Platform: Windows",
    "Platform: Linux",
    "Platform: macOS",
]
timestamp_override = "event.ingested"
type = "eql"
query = '''
process where event.type == "start" and 
event.action in ("exec", "exec_event", "start", "ProcessRollup2", "executed", "process_started") and
process.name : ("curl", "curl.exe") and 
(
  process.args in ("-T", "--upload-file") or
  (
    (process.args in ("-F", "-d", "--form") or process.args like "--data*") and process.command_line like "*@*"
  )
) and
(
  process.command_line like ("*http:*", "*https:*", "*ftp:*", "*ftps:*") or
  process.command_line regex ".*[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}.*"
) and 
not (
  process.args : (
    "https://*/ap/fleet/*", "https://*/api/saved_objects/*", "http*localhost:*", "http*127.0.0.*", "*ApiKey*", "http*.us-central1.run.app/*",
    "*Authorization*", "*session.id*", "http*.elastic-cloud.com*", "http*.elastic.dev*", "http*.elastic.cloud*", "http*.aws.found.io*",
    "http*.gcp.cloud.es.io*", "http*.cisco.com/api/*", "-u", "http://192.168*",
    "*incoming.telemetry.mozilla.org*", "*cloudamize.com*", "https://analytics.brew.sh/*"
  ) or
  process.args == "--unix-socket" or
  process.parent.name like "clevis*" or
  ?process.parent.executable in ("/usr/bin/clevis-decrypt-tang", "/bin/clevis-decrypt-tang") or
  (
    ?process.parent.executable == "C:\\Windows\\SysWOW64\\cmd.exe" and
    ?process.parent.args like "?:\\*\\temp-app\\caller_batch_*.bat"
  ) or
  (
    ?process.parent.executable == "/opt/rudder/share/commands/agent-run" and
    ?process.parent.command_line == "/bin/sh /opt/rudder/share/commands/agent-run -uRN" and
    process.args like "/var/rudder/reports/ready/*"
  ) or
  (
    ?process.parent.executable like "/var/lib/docker/overlay2/*/merged/usr/bin/bash" and
    ?process.parent.command_line like "bash /home/*/old/scripts/crawler.sh start"
  )
)
'''

[[rule.threat]]
framework = "MITRE ATT&CK"

[[rule.threat.technique]]
id = "T1048"
name = "Exfiltration Over Alternative Protocol"
reference = "https://attack.mitre.org/techniques/T1048/"

[[rule.threat.technique.subtechnique]]
id = "T1048.001"
name = "Exfiltration Over Symmetric Encrypted Non-C2 Protocol"
reference = "https://attack.mitre.org/techniques/T1048/001/"

[[rule.threat.technique.subtechnique]]
id = "T1048.003"
name = "Exfiltration Over Unencrypted Non-C2 Protocol"
reference = "https://attack.mitre.org/techniques/T1048/003/"

[rule.threat.tactic]
id = "TA0010"
name = "Exfiltration"
reference = "https://attack.mitre.org/tactics/TA0010/"
```

## rules/cross-platform/exfiltration_third_party_cloud_storage_client_execution.toml
```toml
[metadata]
creation_date = "2026/09/14"
integration = ["endpoint"]
maturity = "production"
updated_date = "2026/09/14"

[rule]
author = ["Elastic"]
description = """
Identifies execution of a third-party S3 or object-storage client (S3 Browser, s5cmd, s3cmd, MinIO mc, rclone,
Cyberduck, s3fs, goofys, juicefs) launched by a script interpreter, a shell one-liner, or from a temporary or
user-writable path. After stealing cloud credentials, adversaries switch from the AWS CLI to these clients to
enumerate and drain buckets in bulk. Gating on a scripted context separates post-exploitation automation from
interactive developer use.
"""
false_positives = [
    """
    Data engineers and DevOps teams legitimately use rclone, s5cmd, and s3cmd for bulk data transfers. This rule
    gates on a scripted parent to suppress interactive use, but automation pipelines that shell out to these tools
    may still trigger alerts. The 7-day new-terms window suppresses recurring invocations of the same client on the 
    same host after the first alert. Allowlist known pipeline executor paths if additional tuning is needed.
    """,
]
from = "now-9m"
index = ["logs-endpoint.events.process*"]
language = "kuery"
license = "Elastic License v2"
name = "Potential Third-Party Cloud Storage Client Execution"

note = """## Triage and analysis

### Investigating Potential Third-Party Cloud Storage Client Execution

This rule fires when a third-party S3 or object-storage client (rclone, s5cmd, s3cmd, MinIO `mc`, S3 Browser, Cyberduck, s3fs, goofys, juicefs, aws-shell) starts under a scripted context: a script interpreter or shell one-liner as parent, or the client or its parent running from a temporary or user-writable path. These tools are common on developer and data-engineering hosts, so the scripted gate is what separates post-exploitation automation from interactive use. After stealing cloud credentials from a compromised server, adversaries drop one of these clients to enumerate, mirror, and then delete bucket contents faster than the AWS CLI allows.

### Possible investigation steps

- Identify the client and the verb from `process.args`: `cp`, `sync`, `mirror`, `mv`, `rm`, `rb` indicate bulk transfer or deletion; `ls`, `find`, `du` indicate enumeration. Note the source and destination, especially a remote endpoint that is not one of your accounts.
- Walk the parent chain. A `sh -c`, `python`, or `node` parent, or a parent in `/tmp`, `/dev/shm`, or `%TEMP%`, is the scripted context the rule keys on. Find what launched that parent (web server worker, cron, CI runner, SSH session, remote management tool).
- Determine where the credentials came from. Check for `~/.aws/credentials`, `.env` files, `rclone.conf`, `~/.s3cfg`, `~/.mc/config.json`, environment variables in the parent process, or instance metadata access from the same host shortly before.
- Pivot to CloudTrail (or the equivalent provider log) for the principal and the host's egress IP: `ListBuckets`, `ListObjects*`, `GetObject`, `DeleteObject*`, and `PutBucketLifecycle` in volume within the same window confirm data access; `GetCallerIdentity` immediately before is a common first call.
- Check the client's user agent in bucket access logs or CloudTrail; S3 Browser, s5cmd, and rclone identify themselves and the `S3 Uncommon Client User Agent` rule may have fired for the same principal.
- Correlate with other alerts on the host and principal: credential file access, `Potential Data Exfiltration via Rclone` on Windows, new IAM keys, or bucket policy and versioning changes.

### False positive analysis

- Backup, replication, and data-pipeline jobs that shell out to `rclone`, `s5cmd`, or `mc` from cron, systemd timers, Airflow, or CI runners. Confirm the job, then add an exception on `process.parent.executable` or the runner path, not on the client name.
- Developers running these clients from a script in a checked-out repository. Verify the repository, the destination bucket, and that the credentials used belong to the developer.
- Configuration and health-check invocations such as `rclone config`, `rclone listremotes`, or `mc alias set`. These are low risk on their own; exclude by argument if they recur.

### Response and remediation

- If the activity is not authorized, isolate the host and terminate the client process and its parent.
- Rotate or revoke every cloud credential present on the host or referenced in the client's configuration. Treat any key the client used as compromised.
- Review the affected buckets for objects downloaded, overwritten, or deleted during the window. Restore from versioning or backups and check for new lifecycle rules, bucket policies, or replication configurations left by the attacker.
- Remove the client binary, its configuration files, and any staged data or scripts, and determine the initial access vector (exposed `.env`, RCE on a web application, leaked key).
- Escalate to the cloud incident response process if the principal had write or delete permissions on production data, or if objects were transferred to an external account.
"""
references = [
    "https://github.com/ramimac/aws-customer-security-incidents",
    "https://unit42.paloaltonetworks.com/large-scale-cloud-extortion-operation/",
    "https://blog.darklab.hk/2021/07/06/trouble-in-paradise/",
]
risk_score = 47
rule_id = "ab05c807-e12b-4ec1-8380-844a65c9fef1"
setup = """## Setup

This rule requires data coming in from Elastic Defend.

### Elastic Defend Integration Setup
Elastic Defend is integrated into the Elastic Agent using Fleet. Upon configuration, the integration allows the
Elastic Agent to monitor events on your host and send data to the Elastic Security app.

#### Prerequisite Requirements:
- Fleet is required for Elastic Defend.
- To configure Fleet Server refer to the [documentation](https://www.elastic.co/guide/en/fleet/current/fleet-server.html).

#### The following steps should be executed in order to add the Elastic Defend integration:
- Go to the Kibana home page and click "Add integrations".
- In the query bar, search for "Elastic Defend" and select the integration to see more details about it.
- Click "Add Elastic Defend".
- Configure the integration name and optionally add a description.
- Select the type of environment you want to protect, either "Traditional Endpoints" or "Cloud Workloads".
- Enter a name for the agent policy in "New agent policy name". If other agent policies already exist, you can
  click the "Existing hosts" tab and select an existing policy instead.
- Click "Save and Continue".
- To complete the integration, select "Add Elastic Agent to your hosts" and install Elastic Agent on your hosts.
For more details on Elastic Defend refer to the [helper guide](https://www.elastic.co/guide/en/security/current/install-endpoint.html).
"""
severity = "medium"
tags = [
    "Domain: Endpoint",
    "Domain: Cloud",
    "Platform: AWS",
    "Platform: Linux",
    "Platform: macOS",
    "Platform: Windows",
    "OS: Linux",
    "OS: macOS",
    "OS: Windows",
    "Service: AWS S3",
    "Tactic: Exfiltration",
    "Tactic: Collection",
    "Use Case: Threat Detection",
    "Resources: Investigation Guide",
    "Data Source: Elastic Defend",
    "Rule Type: New Terms",
]
timestamp_override = "event.ingested"
type = "new_terms"

query = '''
event.category : "process" and event.type : "start" and
process.name : (
  Cyberduck or S3Browser.exe or aws-shell or cyberduck or duck or duck.exe or
  goofys or juicefs or mc or mc.exe or rclone or rclone.exe or
  s3browser-con.exe or s3browser.exe or s3cmd or s3cmd.exe or s3fs or s5cmd or s5cmd.exe or
  *bucketexplorer* or *cloudberry* or *s3browser*
) and not (
  process.name : (mc or mc.exe) and not
  process.args : (admin or alias or cat or cp or du or find or get or ls or mb or mirror or mv or pipe or put or rb or rm or share or stat or tree)
) and not process.executable : (/opt/Elastic/Agent/* or /usr/lib/systemd/*) and
not process.args : (--help or --version or -h or selfupdate or version) and
(
  process.parent.name : (
    bun or bun.exe or cscript.exe or deno or deno.exe or mshta.exe or node or node.exe or nodejs or
    perl* or php* or python* or ruby* or wscript.exe
  ) or
  (
    process.parent.name : (bash or bash.exe or cmd.exe or dash or fish or ksh or powershell.exe or pwsh or pwsh.exe or sh or zsh) and
    process.parent.args : ("-Command" or "-EncodedCommand" or "-enc" or "-e" or "-c" or "-ilc" or "-lc" or "/c")
  ) or
  process.executable : (
    *\\Users\\*\\AppData\\Local\\Temp\\* or *\\Users\\Public\\* or *\\Windows\\Temp\\* or
    /Users/Shared/* or /dev/shm/* or /private/tmp/* or /tmp/* or /var/tmp/*
  ) or
  process.parent.executable : (
    *\\Users\\*\\AppData\\Local\\Temp\\* or *\\Users\\Public\\* or *\\Windows\\Temp\\* or
    /Users/Shared/* or /dev/shm/* or /private/tmp/* or /tmp/* or /var/tmp/*
  )
)
'''

[[rule.threat]]
framework = "MITRE ATT&CK"

[[rule.threat.technique]]
id = "T1537"
name = "Transfer Data to Cloud Account"
reference = "https://attack.mitre.org/techniques/T1537/"

[[rule.threat.technique]]
id = "T1567"
name = "Exfiltration Over Web Service"
reference = "https://attack.mitre.org/techniques/T1567/"

[[rule.threat.technique.subtechnique]]
id = "T1567.002"
name = "Exfiltration to Cloud Storage"
reference = "https://attack.mitre.org/techniques/T1567/002/"

[rule.threat.tactic]
id = "TA0010"
name = "Exfiltration"
reference = "https://attack.mitre.org/tactics/TA0010/"

[[rule.threat]]
framework = "MITRE ATT&CK"

[[rule.threat.technique]]
id = "T1530"
name = "Data from Cloud Storage"
reference = "https://attack.mitre.org/techniques/T1530/"

[rule.threat.tactic]
id = "TA0009"
name = "Collection"
reference = "https://attack.mitre.org/tactics/TA0009/"

[rule.new_terms]
field = "new_terms_fields"
value = ["host.id", "process.name"]
[[rule.new_terms.history_window_start]]
field = "history_window_start"
value = "now-7d"
```

## rules/integrations/anthropic/exfiltration_anthropic_high_file_upload_activity.toml
```toml
[metadata]
creation_date = "2026/09/15"
integration = ["anthropic"]
maturity = "production"
updated_date = "2026/09/25"

[rule]
author = ["Elastic"]
description = """
Detects an unusually high volume of Claude file uploads from the same user email and source IP within a rolling 24-hour
period. Sustained upload activity can indicate staging of sensitive documents in Claude chats for later retrieval,
automated ingestion of data into LLM workflows, or abuse of organizational Claude access to move files into the cloud
service.
"""
false_positives = [
    """
    Developers, analysts, or knowledge workers bulk-uploading documents during migrations, evaluations, or large project
    onboarding can exceed the daily threshold from a single workstation or VPN egress.
    """,
]
from = "now-24h"
interval = "1h"
language = "esql"
license = "Elastic License v2"
name = "Anthropic High File Upload Activity"
note = """## Triage and analysis

### Investigating Anthropic High File Upload Activity

One `user.email` + `source.ip` pair uploaded a large volume of Claude files in 24 hours — possible staging for later
retrieval, automated ingestion, or abuse of org Claude access.

Unauthorized / escalate when filenames look sensitive, uploads target shared/sensitive projects, UA looks automated
(curl/python vs browser), or artifact sharing / exports follow. Close as FP for documented migrations, RAG pilots, or
batch attach jobs with expected project IDs.

#### Possible investigation steps

- Start with `Esql.event_count`, `Esql.file_name_values`, and chat/project ID lists — sensitive names or shared
  project IDs raise priority.
- Triage `user_agent` on raw uploads: browser-like vs scripting clients. Scripting UAs with many distinct file IDs
  look more like automation than interactive work.
- Pivot raw `logs-anthropic.audit-*` for individual `anthropic.audit.claude_file_id` / filenames and whether
  `claude_file_viewed` or chat activity matches the upload volume.
- Correlate with artifact sharing, data exports, or compliance key creation from the same user.

### False positive analysis

- Document migrations and RAG indexing from one seat commonly exceed the threshold.

### Response and remediation

- On unauthorized staging: revoke sessions, review uploaded names/file IDs for sensitive content, and tighten project
  sharing or upload policy for the actor.
"""
references = ["https://platform.claude.com/docs/en/api/compliance/activities/list"]
risk_score = 47
rule_id = "58295a79-5dde-4fc9-a967-2dbe39fb8bc7"
severity = "medium"
tags = [
    "Domain: GenAI",
    "Platform: Anthropic",
    "Data Source: Anthropic Audit Logs",
    "Use Case: Threat Detection",
    "Use Case: UEBA",
    "Resources: Investigation Guide",
    "Rule Type: ES|QL",
    "Tactic: Exfiltration",
    "Mitre Atlas: AML.T0025",
]
timestamp_override = "event.ingested"
type = "esql"

query = '''
from logs-anthropic.audit-*
| where
    data_stream.dataset == "anthropic.audit" and
    event.action == "claude_file_uploaded" and
    event.outcome == "success" and
    user.email is not null and
    source.ip is not null
| stats
    Esql.event_count = count(*),
    Esql.event_id_values = values(event.id),
    Esql.file_name_values = values(file.name),
    Esql.anthropic_audit_claude_file_id_values = values(anthropic.audit.claude_file_id),
    Esql.anthropic_audit_claude_chat_id_values = values(anthropic.audit.claude_chat_id),
    Esql.anthropic_audit_claude_project_id_values = values(anthropic.audit.claude_project_id),
    Esql.user_agent_original_values = values(user_agent.original),
    Esql.anthropic_audit_actor_type_values = values(anthropic.audit.actor.type),
    Esql.timestamp_first_seen = min(@timestamp),
    Esql.timestamp_last_seen = max(@timestamp)
  by user.email, source.ip
| where Esql.event_count >= 100
| keep user.email, source.ip, Esql.*
'''


[[rule.threat]]
framework = "MITRE ATT&CK"
[[rule.threat.technique]]
id = "T1567"
name = "Exfiltration Over Web Service"
reference = "https://attack.mitre.org/techniques/T1567/"


[rule.threat.tactic]
id = "TA0010"
name = "Exfiltration"
reference = "https://attack.mitre.org/tactics/TA0010/"
[[rule.threat_mappings]]
framework = "MITRE ATLAS"
version = "2026.08"
[[rule.threat_mappings.threat]]
framework = "MITRE ATLAS"
[[rule.threat_mappings.threat.technique]]
id = "AML.T0025"
name = "Exfiltration via Cyber Means"
reference = "https://atlas.mitre.org/techniques/AML.T0025/"


[rule.threat_mappings.threat.tactic]
id = "AML.TA0010"
name = "Exfiltration"
reference = "https://atlas.mitre.org/tactics/AML.TA0010/"

[rule.alert_suppression]
group_by = ["user.email", "source.ip"]
missing_fields_strategy = "suppress"

[rule.investigation_fields]
field_names = [
    "user.email",
    "source.ip",
    "Esql.event_count",
    "Esql.event_id_values",
    "Esql.file_name_values",
    "Esql.anthropic_audit_claude_file_id_values",
    "Esql.anthropic_audit_claude_chat_id_values",
    "Esql.anthropic_audit_claude_project_id_values",
    "Esql.user_agent_original_values",
    "Esql.anthropic_audit_actor_type_values",
    "Esql.timestamp_first_seen",
    "Esql.timestamp_last_seen",
]

[rule.alert_suppression.duration]
unit = "h"
value = 24

```

