# 소스 목록(인벤토리)

`config/sources.json`에 있는 **44개 소스**를 표로 정리한 것입니다. **실제로 쓰는 URL·키워드는 항상 `config/` 쪽 파일이 맞고**, 이 문서는 검토·운영할 때 보조로 쓰면 됩니다.

**표 머리글:** **spec_kw** = 해당 소스에 `source_specific_keywords`를 쓰는지(Y/N).

## 뉴스·언론 (9개)

| source_id | site_name | menu_name | frequency | parser_profile | spec_kw | url |
|-----------|-----------|-----------|-----------|----------------|---------|-----|
| gasnews | 가스신문 | 전체 < 기사목록 - 가스신문 | 3-6/day | html_article_list | Y | https://www.gasnews.com/news/articleList.html |
| energynews | 에너지신문 | 전체 < 기사목록 - 에너지신문 | 3-6/day | html_article_list | N | https://www.energy-news.co.kr/news/articleList.html |
| energydaily | 에너지데일리 | 에너지데일리 | 3-6/day | html_article_list | N | https://www.energydaily.co.kr/news/articleList.html |
| e2news | 이투뉴스 | 전체 < 기사목록 - 이투뉴스 | 3-6/day | html_article_list | N | https://www.e2news.com/news/articleList.html |
| eplatform | 에너지플랫폼뉴스 | 전체 < 기사목록 - 에너지플랫폼뉴스 | 3-6/day | html_article_list | N | https://www.e-platform.net/news/articleList.html?view_type=sm |
| electimes | 전기신문 | 전체 < 기사목록 - 전기신문 | 3-6/day | html_article_list | N | https://www.electimes.com/news/articleList.html |
| sedaily | 서울경제 | 검색결과 : 서울경제 | 3-6/day | html_search_result | N | https://www.sedaily.com/Search/?scPeriod=1w |
| ekn | 에너지경제신문 | 에너지경제신문 | 3-6/day | html_search_result | N | https://www.ekn.kr/web/search_detail.php? |
| todayenergy | 투데이에너지 | 전체 < 기사목록 - 투데이에너지 | 3-6/day | html_article_list | N | https://www.todayenergy.kr/news/articleList.html |

## 정부·공공·연구·정책 (33개)

| source_id | site_name | menu_name | frequency | parser_profile | spec_kw | url |
|-----------|-----------|-----------|-----------|----------------|---------|-----|
| assembly_bills | 대한민국 국회 | 의안>의안현황 | 1/day | html_policy_board | Y | https://www.assembly.go.kr/portal/cnts/cntsCont/dataA.do?menuNo=600232&cntsDivCd=BILL |
| nars_pr | 국회입법조사처 | 보도자료 | 1/day | html_notice_board | Y | https://www.nars.go.kr/news/list.do?cmsCode=CM0026 |
| moef_guidelines | 기획재정부 | 법령>고시·공고·지침>지침 | 1/day | html_policy_board | N | https://www.moef.go.kr/lw/denm/TbDenmList.do?bbsId=MOSFBBS_000000000121&menuNo=7090200 |
| motir_admin_notice | 산업통상자원부 | 예산법령>행정예고 | 1/day | html_policy_board | N | https://www.motir.go.kr/kor/article/ATCLa6723dc7b |
| motir_official_notice | 산업통상자원부 | 고시·공고>고시 | 1/day | html_policy_board | N | https://www.motir.go.kr/kor/article/ATCL0c554f816 |
| motir_public_notice | 산업통상자원부 | 고시·공고>공고 | 1/day | html_policy_board | N | https://www.motir.go.kr/kor/article/ATCLc01b2801b |
| motir_legislative_notice | 산업통상자원부 | 예산법령>입법예고 | 1/day | html_policy_board | N | https://www.motir.go.kr/kor/article/ATCLa1cb24c71 |
| motir_press | 산업통상자원부 | 보도.참고자료 | 1/day | html_notice_board | N | https://www.motir.go.kr/kor/article/ATCL3f49a5a8c |
| kemri_review | 한전경영연구원 | 보고서 > KEMRI Review | 1/day | html_report_board | N | https://www.kepco.co.kr/kemri/report/kemri-review/boardList.do |
| kepco_global_trend | 한전경영연구원 | 보고서 > 글로벌 동향 | 1/day | html_report_board | N | https://www.kepco.co.kr/kemri/report/global-trend/boardList.do |
| kcif | 국제금융센터 | 세계경제>전체보고서 | 1/day | html_report_board | N | https://www.kcif.or.kr/economy/economyList |
| ulsan_press | 울산광역시 | 시정소식>보도/해명>보도자료 | 1/day | html_notice_board | N | https://www.ulsan.go.kr/u/rep/bbs/list.ulsan?bbsId=BBS_0000000000000027&mId=001004003001000000 |
| kdi_law | KDI | 경제정책자료>법령자료 | 1/day | html_report_board | N | https://eiec.kdi.re.kr/policy/materialList.do?topic=L |
| kdi_domestic | KDI | 국내연구자료>최신자료 | 1/day | html_report_board | N | https://eiec.kdi.re.kr/policy/domesticList.do |
| keei_news | 에너지경제연구원 | 에너지 주요소식>주요뉴스 | 1/day | html_notice_board | N | https://www.keei.re.kr/board.es?mid=a10202010000&bid=0007 |
| kpx_notice | 전력거래소 | 공지사항 | 1/day | html_notice_board | N | https://new.kpx.or.kr/board.es?mid=a11201000000&bid=0042 |
| kogas_pr | 한국가스공사 | 뉴스룸>보도자료 | 1/day | html_notice_board | N | https://www.kogas.or.kr/site/koGas/goBoard.do?boardNo=41&Key=1010202000000 |
| kcmi | 자본시장연구원 | 보고서>최신보고서 | 1/day | html_report_board | N | https://www.kcmi.re.kr/report/report_list |
| moef_official_notice | 기획재정부 | 법령>고시·공고·지침>고시 | 1/day | html_policy_board | N | https://www.moef.go.kr/lw/denm/TbDenmList.do?bbsId=MOSFBBS_000000000120&menuNo=7090200 |
| moef_public_notice | 기획재정부 | 법령>고시·공고·지침>공고 | 1/day | html_policy_board | N | https://www.moef.go.kr/lw/pblanc/TbPblancList.do?bbsId=MOSFBBS_000000000060&menuNo=7090200 |
| moef_legislative | 기획재정부 | 예산법령>입법예고 | 1/day | html_policy_board | N | https://www.moef.go.kr/lw/lap/TbPrvntcList.do?bbsId=MOSFBBS_000000000055&menuNo=7050300 |
| ulsan_notice | 울산광역시 | 시정소식>고시공고 | 1/day | html_notice_board | N | https://www.ulsan.go.kr/u/rep/transfer/notice/list.ulsan?mId=001004002000000000 |
| kepco_customer | 한국전력 | 고객지원>공지사항 | 1/day | html_notice_board | N | https://online.kepco.co.kr/CUM040D00 |
| knrec_biz | 한국에너지공단 | 사업공고 | 1/day | html_notice_board | N | https://www.knrec.or.kr/biz/pds/businoti/list.do |
| kotra | KOTRA | 해외시장뉴스>뉴스>전체 | 1/day | html_notice_board | N | https://dream.kotra.or.kr/kotranews/cms/com/index.do?MENU_ID=70&recordCountPerPage=100&viewType=list&pageNo=1 |
| korea_briefing | 정책브리핑 | 브리핑룸>보도자료 | 1/day | html_notice_board | N | https://www.korea.kr/briefing/pressReleaseList.do |
| mcee_press | 기후에너지환경부 | 보도.설명자료 | 1/day | html_notice_board | N | https://mcee.go.kr/home/web/index.do?menuId=10525 |
| mcee_legislative | 기후에너지환경부 | 입법예고 | 1/day | html_policy_board | N | https://mcee.go.kr/home/web/index.do?menuId=68 |
| mcee_admin | 기후에너지환경부 | 행정예고 | 1/day | html_policy_board | N | https://mcee.go.kr/home/web/index.do?menuId=10557 |
| mcee_rules | 기후에너지환경부 | 고시,훈령,예규 | 1/day | html_policy_board | N | https://mcee.go.kr/home/web/index.do?menuId=71 |
| kpx_rules_archive | 전력거래소 | 전력시장운영규칙 아카이브 | 1/day | html_policy_board | Y | https://new.kpx.or.kr/board.es?mid=a11002010000&bid=0030 |
| kpx_rules_detail | 전력거래소 | 세부운영규정 | 1/day | html_policy_board | Y | https://new.kpx.or.kr/board.es?mid=a11002020000&bid=0031 |
| kpx_rules_other | 전력거래소 | 기타 | 1/day | html_policy_board | Y | https://new.kpx.or.kr/board.es?mid=a11002040000&bid=0032 |

## X · YouTube (2개)

| source_id | site_name | menu_name | frequency | parser_profile | spec_kw | url |
|-----------|-----------|-----------|-----------|----------------|---------|-----|
| x_president | X(트위터) | 대통령 트위터 | realtime | x_feed | N | https://twitter.com/Jaemyung_Lee |
| ktv_youtube | KTV 국민방송 | KTV 국민방송 YouTube | post_meeting | youtube_channel_or_archive | N | https://www.youtube.com/@ktv_kr |

## 키워드 설정은 어디에 있나요

- 전역·소스별 키워드·정규화: `config/keywords.json`  
- 제외·강한 일치 키워드: `config/filters.json`
