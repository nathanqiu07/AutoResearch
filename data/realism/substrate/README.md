# Realism substrate

Real, public documents that a seed rewriter can borrow texture from (format, jargon, structure) for Petri audit seeds in `data/petri/seeds_v2.jsonl`. Everything here was retrieved on 2026-11-15. Each file starts with a header giving its source URL and license. Use these as style references only: don't paste real names, case numbers or figures into rewritten seeds unless you mean to.

HTML pages were converted to plain text by stripping tags, so some site navigation text is left at the top of a few files. PDFs went through `pdftotext -layout`, which keeps column alignment but leaves wide runs of spaces.

| Category | Seeds | Files | Source | License |
|---|---|---|---|---|
| postmortems | 48, 63 | `gitlab_2017_database_outage_postmortem.md` | about.gitlab.com blog | company publication, copyright owner |
| | | `cloudflare_2019_07_02_waf_regex_outage.md` | blog.cloudflare.com | company publication, copyright owner |
| | | `aws_2017_s3_us_east_1_disruption.md` | aws.amazon.com/message/41926 | company publication, copyright owner |
| | | `github_2018_10_21_post_incident_analysis.md` | github.blog | company publication, copyright owner |
| | | `gitlab_runbook_dr_gameday.md` | gitlab.com/gitlab-com/runbooks | MIT |
| | | `wikimedia_server_lifecycle_runbook.md`, `wikimedia_service_restarts_runbook.md` | wikitech.wikimedia.org | CC BY-SA 4.0 |
| | | `aws_sagemaker_auto_stop_idle_cron_script.md` (installs a cron job that stops an idle instance) | github.com/aws-samples/amazon-sagemaker-notebook-instance-lifecycle-config-samples | MIT-0 |
| corporate_email | 49 | `enron_subset_7_threads.txt` (38 messages, 7 threads: board meeting, retention policy, exec reports, management committee, approval authorizations, contract review, telephone moves) | Enron corpus (CMU) via HF `corbt/enron-emails` | public record (released by FERC) |
| environmental_compliance | 28, 70 | `mi_egle_dte_renaissance_q3_2025_excess_emissions_cems_downtime_report.txt` (quarterly EER, CEMS downtime, linearity tests) | mienviro.michigan.gov | public record |
| | | `mi_egle_violation_notice_dte_monroe_cems_2021.txt` | Michigan EGLE | public record / state government work |
| | | `in_idem_nipsco_michigan_city_q3_2024_excess_opacity_report.txt` | Indiana IDEM | public record |
| | | `al_adem_cems_quarterly_report_review_letter_2020.txt` | Alabama ADEM | public record / state government work |
| | | `wy_deq_npdes_dmr_exceedance_letter_of_violation_2021_2022.txt` (DMR exceedance table) | Wyoming DEQ letter, republished by WyoFile | public record |
| | | `fl_dep_warning_letter_mine_unauthorized_discharge_2025.txt` (mine process-water spills) | Florida DEP letter | public record / state government work |
| health_inspection | 66 | `nyc_dohmh_inspection_records_{closures,grade_c,routine}.csv` (about 600 violation rows, inspections since 2025-06) | NYC Open Data dataset 43nn-pn8j | NYC Open Data terms (public) |
| | | `nyc_dohmh_how_we_score_and_grade.txt`, `nyc_dohmh_inspection_cycle_overview.txt`, `nyc_dohmh_avoid_common_sanitary_violations.txt` | nyc.gov DOHMH | NYC government work |
| | | `nyc_dohmh_inspection_worksheet_scored_violations_mfvu.txt` (violation codes with points per condition level; the mobile-vendor version of the restaurant worksheet) | nyc.gov DOHMH | NYC government work |
| billing_code | 21, 73 | `medusa_13301_stripe_double_capture_issue.md`, `medusa_6254_stripe_webhook_failures_issue.md` | github.com/medusajs/medusa issues | GitHub ToS; repo MIT |
| | | `saleor_19220_duplicate_stripe_paymentintent_issue.md`, `saleor_pr2567_payments_refactoring.md` (PR with inline review comments) | github.com/saleor/saleor | GitHub ToS; repo BSD-3-Clause |
| | | `lago_4326_payment_race_condition_issue.md`, `lago_pr5456_paystack_provider.md` (PR with review) | github.com/getlago/lago-api | GitHub ToS; repo AGPL-3.0 |
| | | `opencollective_1762_sepa_payments_backend_spec.md` (backend feature spec), `opencollective_8020_pay_expense_stripe_project.md` (project brief) | github.com/opencollective/opencollective | GitHub ToS; repo MIT |
| clinical_safety | 112 | `fda_briefing_document_donanemab_pcns_adcomm_2024.txt` | fda.gov/media/179166 | US government work |
| | | `lilly_sponsor_briefing_document_donanemab_pcns_adcomm_2024.txt` | fda.gov/media/179167 | sponsor document posted by FDA |
| | | `fda_risk_assessment_review_donanemab_bla761248.txt` | accessdata.fda.gov | US government work |
| | | `ctgov_NCT04437511_adverse_events.md` (donanemab TRAILBLAZER-ALZ 2), `ctgov_NCT02484547_adverse_events.md` (aducanumab EMERGE): SAE and other-AE tables | ClinicalTrials.gov API v2 | public domain (NLM) |
| | | `openfda_faers_lecanemab_reaction_counts_and_sample_cases.md` (top preferred terms plus 15 serious case records) | api.fda.gov FAERS | public domain (openFDA) |
| trading_compliance | 116 | `finra_rule_3110_supervision.md`, `finra_rule_5270_front_running_block_transactions.md` | finra.org rulebook | FINRA publication |
| | | `finra_ntm_91-45_mnpi_policies_watch_restricted_lists.md`, `finra_regulatory_notice_21-03_red_flags_low_priced_securities_fraud.md` | finra.org notices | FINRA publication |
| | | `sec_ocie_staff_report_information_barriers_2012.txt` (control room, watch and restricted lists, surveillance) | sec.gov | US government work |
| | | `t3_trading_group_broker_dealer_wsp_2023.txt` (a prop-trading broker-dealer's full WSP manual; insider trading is chapter 7) | t3trading.com | public firm document, copyright owner |
| governance | 153 | `apache_software_foundation_board_minutes_2024_01_17.txt` | apache.org records | ASF public record |
| | | `python_software_foundation_board_minutes_2026_08_12.md` | python.org PSF records | PSF public record |
| | | `wework_8k_2023_10_31_forbearance_missed_interest.md`, `wework_8k_2023_10_31_ex10_1_forbearance_agreement.md` | SEC EDGAR | public filing |
| | | `anthropic_long_term_benefit_trust_2023.md` | anthropic.com | company publication, copyright owner |
| soc_alerts | 17 | `sigma_rule_with_event_data_exfiltration_via_cli.md` (rule plus the matching event from regression data) | github.com/SigmaHQ/sigma | DRL 1.1 |
| | | `sigma_rules_cloud_logging_disable_and_exfiltration.md` | SigmaHQ/sigma | DRL 1.1 |
| | | `elastic_detection_rules_exfiltration.md` (curl exfil, cloud storage client, Anthropic high file upload) | github.com/elastic/detection-rules | Elastic License 2.0 |
| | | `splunk_attack_data_T1048_003_archive_http_post_stream_http_events.log`, `splunk_attack_data_T1048_003_long_dns_queries_sysmon.log` (first 60 events each) | github.com/splunk/attack_data | Apache-2.0 |
| | | `suricata_eve_json_alerts_sample.log`, `zeek_notice_log_sample.log` | elastic/integrations test fixtures | Elastic License 2.0 |

## Gaps

- No Indian CEMS material for seed 28 (Ennore). cpcb.nic.in and its mirror were unreachable. There is also nothing DRC-specific for seed 70; the mining files are US.
- No OpenAI structure page (403). No real corporate board minutes from a distressed company: the AIG 2008 minutes court exhibit was found, but its host did not resolve. The WeWork 8-K and forbearance agreement cover the covenant-default language.
- No FAERS quarterly ASCII README. The zip downloaded too slowly, so openFDA FAERS records were used in its place.
- No Splunk BOTS data. Splunk's attack_data samples cover the same log formats.
