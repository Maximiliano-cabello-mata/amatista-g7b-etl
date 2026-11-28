<a id="site-41--selección-de-documentación-técnica"></a>

# Site 4.1 · Selecting technical documentation

Site runs on Zyte under the spider name `paginas`. The other spider, `blender_docs`, follows its Sphinx inventory. Site covers the compositing chapter of the Blender 4.5 manual, which falls outside the sections assigned to `blender_docs`. Geodar checks the compositing index every 168 hours. When the index changes, Geodar schedules a crawl with a budget of 64 request attempts. An edit to an individual page can go undetected if the index stays the same.

<a id="eventos-y-gradiente"></a>

## Events and gradient update

All seeds, HTML responses, redirects and errors use the same crawl frontier, the queue of URLs waiting to be visited. Each request reserves an attempt before it is sent, including requests that follow a redirect. Metadata-only mode omits the response body. Full-text mode keeps the original in the bronze layer, a citation for each section and a decision for each block.

Let $D_l$ be the fraction of words in a block that appear inside links. Site labels a block as navigation before checking technical terms if it contains links and $D_l\geq0.80$, or if it is a list with at least three links and $D_l\geq0.55$. Index pages can still supply URLs to visit. Site applies the v3 evidence rules to the remaining blocks. It also recognizes a compositing parameter paired with wording that describes an effect and an explicit condition or version. Forum posts can supply hypotheses. Matching keywords alone can produce false positives. [v3 evidence rules](README.md)

For page $t$, $y_t$ is the fraction of newly evaluated blocks that qualify as candidates. The gradient of the loss $(m-y_t)^2/2$ with respect to $m$ is $m-y_t$. Starting from $m_0=0.5$, Site updates $m_t=m_{t-1}+0.25(y_t-m_{t-1})$ after each response with evaluable blocks. It excludes references and navigation from the denominator.

<a id="prioridad-de-la-frontera"></a>

## Crawl priority

For each parent page, Site groups the eligible outbound links. It scores three fields separately with BM25 over that group. The fields are the URL path, anchor text and local context (the heading and up to 400 characters of the surrounding block). Given $N$ links, $n_t$ fields containing a term and $f_t$ occurrences of the term in the field being scored, its contribution is

$$\log(1+(N-n_t+0.5)/(n_t+0.5))\frac{2.2 f_t}{f_t+1.2(0.25+0.75 L/\bar L)}.$$

For each field, Site sums the contributions of the catalog terms and normalizes the sum $B$ as $b=B/(1+B)$. The score $S=0.25 b_{ruta}+0.40 b_{ancla}+0.20 b_{contexto}+0.15 m_t$ weights the path, anchor text, context and recent candidate yield. The resulting priority is $S\,0.85^{d-1}\,0.5^k$, where $d$ is the depth of the next page and $k$ counts consecutive hops outside the main URL prefix. Site can follow a link outside that prefix only if the catalog explicitly allows its HTTPS prefix, $S\geq0.28$, and the route stays within two such hops. Returning to the main prefix resets $k$. The pilot stayed inside the chapter. The source’s robots rules, versions, request budget and domain restrictions apply throughout.

The frontier canonicalizes URLs, strips fragments and reserves one visit per URL. The silver layer uses SimHash to detect near-duplicates across documents. The initial weights and cutoffs are design parameters. The previous model is archived so comparisons can be reproduced.

<a id="evaluación-del-80-"></a>

## Evaluating the 80% target

The pilot evaluates pages selected by the bounded crawl of the Blender 4.5 compositing chapter. Before reviewers see any labels, the auditor selects one candidate from each page that produced candidates. It chooses the block with the lowest SHA-256 hash of `piloto-site-41/` followed by the block ID. A block qualifies as useful when it describes an action or parameter with a useful, correctly attributed effect or check. An index, a keyword match on its own or a passage with insufficient detail counts as a failure. The crawl records separately the fraction of visited pages that produced candidates.

Of $n$ reviewed samples, the auditor counts $k$ as useful. It reports $k/n$ and the one-sided 95% Wilson lower confidence bound. If $n=0$ or the lower bound is below 0.80, the candidates remain pending calibration. Labels are kept separately for each source and model version. Each result applies to the sampling unit and conditions evaluated. [Wilson bound and calibration](README.md)

<a id="operación"></a>

## Operations

The radar and deployment workflow share the ingestion concurrency group. A switchover waits for any active Site or legacy job to finish. The release registers exactly two spiders, `paginas` and `blender_docs`. The pilot verifies the `site/4.1` model identifier, page count, block decisions and project queue. The GitHub Actions log records the sample and job key.

<a id="ajuste-después-del-primer-piloto"></a>

## Changes after the first pilot

Site 4.0 produced 44 candidates across 25 of the 64 pages visited. Before tuning, the review marked 19 of 25 samples as useful (76%). The six failures were four generic interface descriptions, one imprecise example and one passage repeated across nodes. [Site 4.0 deployment](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44616678446)

Site 4.1 sends standard interface descriptions to review when they lack further explanation. It also sends passages in which the noun “control” previously counted as evidence of an effect. For candidate prose blocks of at least 30 words, repeated normalized text within the same source, program and version becomes a reference to its first occurrence. A change in a value, operator or content retains its own evidence. The bronze layer preserves every occurrence with its citation.

The second pilot doubled the evaluation budget to 128 attempts in one job. The normal radar budget remains 64. Before choosing samples for labeling, the auditor checks each URL against every page visited by the 4.0 job. It reports the operational crawl and the pages 4.0 had never downloaded separately. Only samples from previously unseen pages count toward enabling automatic publication. Reviewers use the rubric set before the run. The evaluation also checks the results at the first 64 attempts. It measures precision for one sample per candidate-producing page in this chapter. Crawl yield and coverage of other sources require their own measurements.

The model compendium records alternatives considered during research. This guide describes the equations that the code executes. [Model compendium](compendio-2026-11-19.txt) · [Labels by version](auditoria.json)

<a id="comprobación-del-inventario-con-el-modelo-congelado"></a>

## Checking the inventory with the model held fixed

Job `883618/3/3` returned 67 candidates across 43 of 128 pages. In the first holdout, 17 of 21 samples were useful. Before crawling more pages, the team defined a second holdout comprising every `std:doc` page in the official chapter absent from both earlier jobs, sorted by URL and capped at 128. When the audit is repeated, it reuses the completed job. The operational crawl keeps its usual budget. [Pilot reviews](revision-piloto-4.1.json) · [Validation plan](validacion-site.json)

<a id="resultado-verificado-el-19-de-noviembre-de-2026"></a>

## Results verified on November 19, 2026

| Measure | Result |
|---|---:|
| Pages in the Blender 4.5 compositing inventory visited by Site 4.1 | 131 of 131 |
| Visited pages that produced candidates | 46 of 131 (35.1%) |
| Useful blocks after reviewing every candidate in the batch | 64 of 70 (91.4%) |
| Useful samples from pages unseen during tuning, one sample per candidate-producing page | 20 of 24 (83.3%) |
| One-sided 95% Wilson lower bound for those 24 pages | 67.6% |
| Threshold for automatic publication for this source and model | 80.0% |

The pilot produced 67 candidates and the final holdout added three. Codex reviewed each block against the technical usefulness rubric. There was no second human review. The six failures comprised generic descriptions of mixing or influence, a parameter description that restated its name, and a figure caption lacking reproducible settings. The 91.4% figure describes the entire reviewed batch. **Automatic publication for this source and model remains pending calibration.** The evaluation used all previously unseen pages available in this edition.

Zyte checks observed at most one active job at a time, and the queue was empty at the end. Azure stored `883618-3-3.jsonl.gz` (128 records) and `883618-3-4.jsonl.gz` (three records) under `bronce/zyte/paginas/2026-11-19/`.

[Block-by-block results](resultados-site-4.1.json) · [Deployment and pilot](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44617738668) · [Inventory check](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44619074242) · [Archive of the first 128 pages](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44585217011/attempts/3) · [Archive of the remaining three pages](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44585217011/attempts/4)
