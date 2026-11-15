---
source: https://github.com/SigmaHQ/sigma (three rules, paths below)
retrieved: 2026-11-15
license: Detection Rule License (DRL) 1.1 (SigmaHQ)
---

## rules/cloud/aws/cloudtrail/aws_cloudtrail_disable_logging.yml
```yaml
title: AWS CloudTrail Important Change
id: 4db60cc0-36fb-42b7-9b58-a5b53019fb74
status: test
description: Detects disabling, deleting and updating of a Trail
references:
    - https://docs.aws.amazon.com/awscloudtrail/latest/userguide/best-practices-security.html
author: vitaliy0x1
date: 2020-01-21
modified: 2022-10-09
tags:
    - attack.defense-impairment
    - attack.t1685.002
logsource:
    product: aws
    service: cloudtrail
detection:
    selection_source:
        eventSource: cloudtrail.amazonaws.com
        eventName:
            - StopLogging
            - UpdateTrail
            - DeleteTrail
    condition: selection_source
falsepositives:
    - Valid change in a Trail
level: medium
```

## rules/cloud/aws/cloudtrail/aws_snapshot_backup_exfiltration.yml
```yaml
title: AWS Snapshot Backup Exfiltration
id: abae8fec-57bd-4f87-aff6-6e3db989843d
status: test
description: Detects the modification of an EC2 snapshot's permissions to enable access from another account
references:
    - https://web.archive.org/web/20240314115300/https://www.justice.gov/file/1080281/download
author: Darin Smith
date: 2021-05-17
modified: 2021-08-19
tags:
    - attack.exfiltration
    - attack.t1537
logsource:
    product: aws
    service: cloudtrail
detection:
    selection_source:
        eventSource: ec2.amazonaws.com
        eventName: ModifySnapshotAttribute
    condition: selection_source
falsepositives:
    - Valid change to a snapshot's permissions
level: medium
```

## rules-emerging-threats/2025/Malware/Shai-Hulud/proc_creation_lnx_mal_shai_hululd_exfiltration.yml
```yaml
title: Shai-Hulud NPM Package Malicious Exfiltration via Curl
id: efd2eb09-b72e-4a61-8dc7-b1382a1e8983
status: experimental
description: Detects potential Shai Hulud NPM package attack attempting to exfiltrate data via curl to external webhook sites.
references:
    - https://www.getsafety.com/blog-posts/shai-hulud-npm-attack
author: Swachchhanda Shrawan Poudel (Nextron Systems)
date: 2025-09-24
tags:
    - attack.exfiltration
    - attack.t1041
    - attack.collection
    - attack.t1005
    - detection.emerging-threats
logsource:
    category: process_creation
    product: linux
detection:
    selection:
        Image|endswith: '/curl'
        CommandLine|contains|all:
            - 'curl'
            - '-d'
            - 'webhook.site/bb8ca5f6-4175-45d2-b042-fc9ebb8170b7'
    condition: selection
falsepositives:
    - Unlikely
level: high
```

