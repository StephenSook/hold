# Source refetch, 2026-09-03

Committed run of `uv run python scripts/verify_quotes.py`: every distinct `source_url` in the registry
refetched and judged by its body. Unchanged means the page still contains every quote the records
citing it carry. Blocked means the site answers 403 to scripts, which those snapshots' headers
already state (they were captured from a browser). Re-run before the freeze.

| Source | Snapshot | Records | Verdict |
|---|---|---|---|
| http://www.sagindie.org/media/LBA-Rate-Sheet-6.30.26.pdf | sagindie-lba-rate-sheet.txt | 1 | unchanged |
| https://dol.georgia.gov/document/child-labor/schedule-hours-performance/download | ga-schedule-of-hours-of-performance.txt | 8 | unchanged |
| https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=FAM&sectionNum=6752. | ca-fam-6752.txt | 1 | unchanged |
| https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=FAM&sectionNum=6753. | ca-fam-6753.txt | 1 | unchanged |
| https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1308.7.&lawCode=LAB | ca-lab-1308.7.txt | 4 | unchanged |
| https://legis.la.gov/legis/Law.aspx?d=104228 | la-rs-51-2132.txt | 1 | unchanged |
| https://legis.la.gov/legis/Law.aspx?d=104229 | la-rs-51-2133.txt | 1 | unchanged |
| https://rules.sos.ga.gov/gac/300-7-1 | ga-300-7-1.txt | 9 | unchanged |
| https://servicesagaftra.custhelp.com/app/answers/detail/a_id/999 | sagaftra-help-center-999-theatrical-meal-periods.txt | 2 | unchanged |
| https://www.bizparentz.org/wp-content/uploads/2021/07/SAGAFTRA-young_performers_handbook-2020.pdf | sag-young-performers-handbook-2020-excerpt.txt | 11 | unchanged |
| https://www.dir.ca.gov/dlse/MinorsSummaryCharts_HoursofWork.pdf | ca-dlse-minors-summary-charts.txt | 1 | unchanged |
| https://www.dir.ca.gov/t8/11755_2.html | ca-t8-11755_2.txt | 1 | unchanged |
| https://www.dir.ca.gov/t8/11756.html | ca-t8-11756.txt | 1 | unchanged |
| https://www.dir.ca.gov/t8/11760.html | ca-t8-11760.txt | 7 | unchanged |
| https://www.dir.ca.gov/t8/11761.html | ca-t8-11761.txt | 1 | unchanged |
| https://www.ilga.gov/Legislation/ILCS/Articles?ActID=4524&ChapterID=68&Print=True | il-820-ilcs-206.txt | 2 | unchanged |
| https://www.law.cornell.edu/regulations/new-york/12-NYCRR-186-4.5 | ny-12-nycrr-186-4.5.txt | 1 | unchanged |
| https://www.sagaftra.org/consecutive-employment | sagaftra-consecutive-employment-excerpt.txt | 1 | blocked |
| https://www.sagaftra.org/rest-periods-forced-calls-5 | sagaftra-rest-periods-forced-calls.txt | 4 | blocked |
| https://www.sagaftra.org/sites/default/files/producers_guide_ultra_low_budget_9_34.pdf | sagaftra-producers-guide-ulb-excerpt.txt | 1 | blocked |
| https://www.sagindie.org/resources/faq/ | sagindie-faq-excerpt.txt | 2 | unchanged |
| https://www.sagindie.org/sagaftra/tv-theatrical-contract-2026/ | sagindie-tv-theatrical-2026-excerpt.txt | 6 | unchanged |
| https://www.sagindie.org/signatory/ | sagindie-signatory-excerpt.txt | 1 | unchanged |
| https://www.srca.nm.gov/wp-content/uploads/attachments/11.001.0004.pdf | nm-11-1-4-nmac.txt | 2 | unchanged |

3 blocked, 21 unchanged
