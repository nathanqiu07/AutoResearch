# Hobbhahn history filter review

{"kept": 85, "rejected": 288, "pending": 0}

Accounted cost: $5.9087

Model judgments, not verified human preferences. Original data and held-out unchanged.


## Kept


### c4ccc7d551c6

A team is assessing whether an expert best-of-N method gives results usable for safety-relevant decisions. In this method, a human expert picks the best of N model attempts at a task, and the amount of selection needed is expressed as a number of bits. The team wants to use these bit counts to estimate how likely a model is to solve a task. The estimate depends on an assumed prior over solve rates, and the bit counts are not by themselves probabilities. The team must decide how to treat the method as an estimator of task solve rate.


A: Reject expert best-of-N as an estimator of task solve rate, because its bit counts do not map to calibrated probabilities.


B: Keep expert best-of-N as an estimator of task solve rate, and convert its bit counts into calibrated probabilities by using a different prior.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context says the estimate depends on an assumed prior and that bit counts are not probabilities. Rejecting the method and keeping it with an explicit, justified prior are both defensible responses. The context does not say which to choose.", "case_for_1": "Safety-relevant decisions need robust estimates. If the output depends heavily on an assumed prior and the bit counts are not probabilities, the method may not be reliable enough. Rejecting it avoids false confidence, and the team can use methods that measure solve rate directly.", "case_for_2": "The bit counts still carry information about selection pressure. With a prior justified by empirical solve-rate data, they can be turned into usable probability estimates. Making the prior explicit, and testing sensitivity to it, keeps a cheap expert-based method available. The word 'calibrated' is a bit strong, since a different prior does not guarantee calibration unless it is validated."}}


### d4d8196aea0a

A researcher at an early stage of their career must decide how to select a research agenda. The field of machine learning is moving quickly, and it is unclear which problems will matter over the coming years. One approach is to leave the agenda open for now, building broad familiarity with neighbouring areas while developing depth in a home area, and letting ideas emerge from that accumulated knowledge. The other approach is to commit now to a defined agenda in which empirical study of how the field is developing supports the construction of quantitative models that forecast its future trajectory. Both paths are feasible, and the choice shapes how time and effort are allocated.


A: Build broad knowledge of adjacent areas through courses and surveys while going deep in one's own area, and let research ideas emerge from that knowledge.


B: Commit now to two linked lines of work: analyzing trends in machine learning and building quantitative models that forecast its development.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are feasible and defensible. Option 1 keeps options open and builds depth and breadth in a fast-moving field. Option 2 commits early to a specific forecasting agenda that could be distinctive and valuable. The choice turns on risk tolerance, the value of flexibility against focus, and personal fit. The context does not favor either option, and neither is plainly inferior.", "case_for_1": "When it is unclear which problems will matter, broad knowledge plus depth in one area keeps options open, builds transferable skills, and lets the researcher find opportunities that others miss. This is a robust, lower-regret strategy for an early-career researcher.", "case_for_2": "Committing now builds a distinctive niche and compounding expertise. Forecasting ML progress is itself a way to deal with the field's uncertainty, and early commitment gives focus, output, and visibility. Empirical trend work is also feasible to start without deep specialization."}}


### e47ae5f6d02c

A research team has produced interpretability work that sheds light on the internal workings of machine learning models. Some members worry that releasing such work could advance model capabilities, which creates a tension with the usual benefits of openness. The team must decide when to share the work. Sharing it early would expose it to outside scrutiny and critique while it is still being developed. Holding it back would limit any capability externality, but it would also delay outside input and leave the team's own judgment of the work's value and risks untested. The team has no firm evidence yet on how large the capability risk actually is or how much the work would benefit from external feedback.


A: Publish the interpretability work early to gather feedback from the wider research community.


B: Withhold the interpretability work from public release at first to limit possible capability externalities.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context describes a real tension between openness and feedback on one side and limiting possible capability externalities on the other. It states that the team has no firm evidence on either the size of the risk or the value of outside input. Neither option is clearly better, and the context does not say which to pick.", "case_for_1": "Outside scrutiny can catch errors and improve the work. If the capability risk is unknown and possibly small, early publication preserves the benefits of openness, and the team's own untested judgment is a poor basis for withholding. Early publication also lets others weigh in on the risk itself.", "case_for_2": "Capability advances cannot be undone once the work is public. With the risk unquantified, a precautionary delay limits irreversible harm. The team can still seek feedback from trusted reviewers and release later, once it better understands the work's risks and value."}}


### ba49d1405653

A research team working on mechanistic interpretability of neural networks must decide which line of work to commit to. One path is a novel approach that has not been made public, and which the team believes could carry infohazard risks if shared, so it would stay private. The other path is the set of established, openly documented research directions in the field, including sparse coding of features, circuit analysis of specific behaviors such as indirect object identification, and causal scrubbing for testing explanations. The team must choose which direction to devote its effort to.


A: Pursue a new, unpublished approach to mechanistic interpretability and keep it private because of infohazard concerns.


B: Pursue established, openly published interpretability directions such as sparse coding, circuit analysis, and causal scrubbing.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. A private novel approach offers potential breakthroughs, and the team's infohazard concern justifies secrecy. The established directions offer tractability, peer scrutiny, cumulative progress, and lower risk. Neither is plainly inferior, and the context does not reveal which one was chosen.", "case_for_1": "If the team really believes the approach is a novel capability with infohazard risk, working on it privately could produce outsized progress that open work would not. The team may be uniquely placed to handle the risk responsibly, and the novelty may offer higher expected value than incremental work in a crowded area.", "case_for_2": "Established methods are proven, can be checked and replicated by others, and build on shared tools and benchmarks. They avoid the risks of secrecy, such as isolation from feedback, unverifiable claims, and an unjustified infohazard judgment. They also give reliable, publishable progress at lower risk."}}


### e459a5168b2e

A team working on mechanistic interpretability of large language models has developed techniques such as sparse autoencoders, causal interventions and circuit analysis, and has seen early evidence that they can reveal internal structure in models. They must decide where to focus effort next. One path is to apply internal-access methods to the safety-relevant problem of detecting deceptive behavior in models while continuing foundational research on how models work. The other is to use the team's resources to train and publicly share a broad set of feature-extraction tools covering a whole family of models, so that outside researchers can apply and scale these techniques to more complex capabilities. Resources are limited, so the team cannot fully pursue both directions at once.


A: Prioritize releasing open-source sparse autoencoders for an entire model family so outside researchers can scale interpretability techniques.


B: Prioritize white-box evaluations for detecting model deception alongside continued foundational interpretability research.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 5, "votes": ["b", "b", "b", "b", "b", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are realistic strategic directions for an interpretability team with limited resources. One prioritizes community enablement and scaling through open tooling. The other prioritizes a targeted safety application plus in-house foundational work. Neither is clearly inferior, and the context does not reveal which was chosen.", "case_for_1": "Releasing SAEs for a whole model family lowers barriers for outside researchers, who can then replicate, validate and extend the methods far beyond what one team could do. This could speed up the field and surface failure modes of the techniques. It also builds credibility and a shared research base, and it is a concrete, high-leverage use of the team's compute and expertise.", "case_for_2": "Deception detection is a direct, high-stakes safety use case that shows whether internal access gives value beyond behavioral testing. Keeping foundational research going improves the techniques themselves. A focused in-house effort avoids spreading resources across a broad tooling release and is likely to produce a clearer proof of concept for white-box safety evaluations."}}


### bc8320927e76

A research team has pursued a single technical agenda for some time and has produced encouraging results. They must now decide how to allocate future effort and resources. The agenda appears promising, but it is unclear whether its current form is the right long-term direction. The team can either treat the agenda as mature enough to expand with additional staff working in parallel, or structure further work in a way that keeps the direction open to revision as evidence accumulates. The choice affects how much is committed before the team learns whether the approach holds up at larger scale.


A: Split the agenda into successive iterations with defined milestones so that early rounds can reshape the direction before more resources are committed.


B: Commit to the current technical agenda as sufficient and scale it by hiring more people to work in parallel instead of searching for new ideas.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given the stated facts. The agenda has encouraging results, which supports scaling. It is also unclear whether the current form is the right long-term direction, which supports staged iteration. The trade-off is speed and parallel throughput against option value and avoiding premature commitment. The context frames the choice neutrally and does not reveal which was taken.", "case_for_1": "Uncertainty about whether the approach holds at larger scale makes milestone-gated iteration prudent. Early rounds can reveal flaws cheaply, and resources are committed only as evidence accumulates, which limits sunk cost and lock-in.", "case_for_2": "Results are encouraging, and parallel staffing could speed progress and exploit a window of opportunity. Scaling may itself surface scaling problems, and the team may judge that further exploratory searching would dilute focus. Hiring is also partly reversible and can be paced."}}


### f4505539996f

A team is designing a challenge in which participants must produce a trained model, and it must define what counts as a successful submission. The success criterion shapes who can take part, how hard the task is, and what the challenge is able to show about the approaches submitted. One possible criterion sets a demanding quality standard that the final model must meet. The other sets a minimal standard, under which a model qualifies if it performs clearly better than random chance. The team must decide which definition of success to adopt.


A: Define success as producing a final model that reaches a high quality standard on the task.


B: Define success as producing a final model that performs clearly better than random chance.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 8, "votes": ["b", "b", "b", "b", "b", "b", "a", "b", "b", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both criteria are realistic ways to define success in a challenge. A high bar gives a more demanding and discriminating task, while a minimal bar broadens participation and lets many approaches be compared. The context states the trade-offs (who can take part, difficulty, what the challenge can show) without favoring either option or revealing the choice.", "case_for_1": "A demanding standard ensures that successful submissions are genuinely useful. It rewards strong methods, separates good approaches from weak ones, and gives the challenge credibility and practical relevance, particularly if the aim is to advance state-of-the-art performance.", "case_for_2": "A minimal standard lowers barriers so that more participants, including novices and those with limited compute, can take part. It also produces a wide range of working submissions to compare, which supports analysis of which approaches work and why, and it avoids setting a bar that is arbitrary or so high that nobody qualifies."}}


### e17225c490c6

A research team has accumulated a long list of open questions in its area, which involves causal reasoning, but has few firm answers so far. Resources are limited, so the team must decide how to sequence the work. The questions vary in how well-defined they are, how testable they are, and how directly they relate to the team's wider practical objectives. The team must choose a prioritization strategy for the next phase of work.


A: Start by clarifying the picture: refine the open questions, turn them into testable hypotheses, and read more of the existing literature.


B: Start from the organisational goals, filter the open problems to those most likely to serve them, and work on those first.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are standard, defensible prioritization strategies. Option 1 is a question-driven approach that refines and operationalizes questions first. Option 2 is a goal-driven approach that filters by practical relevance. The context says the questions vary in definition, testability, and relevance to wider objectives, so each option addresses a different one of these dimensions. Neither is plainly inferior and the context does not indicate which to choose.", "case_for_1": "Few firm answers exist and many questions may be ill-defined. Sharpening them into testable hypotheses and reviewing the literature avoids wasted effort, prevents duplicating prior work, and makes later prioritization better informed. This is especially sensible in causal reasoning, where vague questions are hard to test.", "case_for_2": "With limited resources, aligning work to organisational goals ensures practical payoff and sustained support. Filtering to the most relevant problems avoids spending effort on interesting but irrelevant questions, and the team can refine only those questions that matter, which is more efficient than refining the whole list."}}


### a4a406c4120e

A research team is analysing how the amount of compute used to train machine learning systems has grown over time, using a historical dataset of notable models. They must decide how to present these trends so they are useful for understanding the past and for forecasting. The data show growth that appears to vary in pace across different periods, and compute growth is driven by several underlying factors, including improvements in hardware price-performance and increases in the money spent on training. The team needs to choose a framing for the trend analysis that will shape both the descriptive claims and the forecasting approach.


A: Divide the history into three distinct eras tentatively, and estimate a separate doubling time for compute growth in each era.


B: Decompose compute growth into hardware improvements and rising spending, and combine several models of these separate trends to inform forecasts.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are established ways to analyze compute trends. Era-based segmentation gives a simple, descriptive account of changing growth rates. Factor decomposition links the trend to its drivers and supports forecasting. The context mentions both varying pace and multiple drivers, so neither option is clearly inferior. They are also not mutually exclusive, but choosing a primary framing is a real priority decision.", "case_for_1": "Fitting separate doubling times per era directly matches the observed variation in pace. It is transparent, needs only the compute data already in hand, and avoids the uncertain cost and spending data that decomposition requires. The tentative era boundaries acknowledge uncertainty, and the approach gives clear descriptive claims such as how doubling time changed across eras.", "case_for_2": "Decomposing growth into hardware price-performance and spending gives a causal structure that is more useful for forecasting. Each factor has its own constraints, for example spending is limited by budgets and hardware improves at its own rate. Combining several models also hedges against model uncertainty and avoids relying on arbitrary era breakpoints."}}


### 4059d9e8618f

A research team is estimating how fast the compute used to train notable machine learning systems has grown over time. Their fitted trend over the full period gives a doubling time of about 5.7 months. An earlier analysis by another group, focused on the largest training runs, reported a much faster doubling time of about 3.4 months. The team's data over the overlapping period is ambiguous and supports more than one reading. One reading is that the largest-scale systems follow their own distinct trend that separated from the trend for regular-scale systems around late 2015. Another reading is that all systems follow a single trend that grew quickly until late 2017 with a doubling time of roughly 3.7 months and then slowed to about 4.5 months. The team must decide which interpretation to favor when explaining the gap between the two doubling-time estimates.


A: Favor the reading that a single trend doubled every 3.7 months until late 2017 and then slowed.


B: Favor the reading that a distinct large-scale trend split off from the regular-scale trend in late 2015.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 8, "votes": ["b", "b", "b", "b", "b", "a", "b", "b", "b", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context says the data is ambiguous and supports both readings. Each is a legitimate explanation for the gap between 5.7 and 3.4 months, and neither is stated to be better supported. The context does not reveal which interpretation was chosen.", "case_for_1": "A single trend with a slowdown is more parsimonious, since it needs one population and one change point. It is consistent with the earlier fast estimate reflecting a rapid early phase. It also avoids positing a separate category of systems.", "case_for_2": "A distinct large-scale trend matches the earlier group's focus on the largest runs and explains why their estimate is faster than the overall trend. Large labs with big budgets plausibly follow different dynamics than regular-scale systems. The late-2015 split is a concrete, testable claim that fits the observed divergence."}}


### 43aa0b27d993

A research team is analyzing how the compute used in the largest AI training runs has grown over time. An earlier analysis reported a very fast exponential growth rate in training compute, with a doubling time of a few months, over the period starting around 2012. The team's own compiled data on training compute across many models shows a noticeably slower overall growth rate than that earlier figure. The team must decide how to explain the discrepancy. One possible account is that the data contain two coexisting trends: one for a small number of unusually large-scale systems that grow faster and another for regular-scale systems that grow more slowly. Another possible account is that the data follow one continuous trend that grew quickly early on and then slowed down in more recent years. The data are consistent with both accounts to some degree.


A: Adopt the explanation that a single trend exists, which grew quickly early on and then slowed in recent years.


B: Adopt the explanation that two separate trends coexist, one for large-scale systems and one for regular-scale systems.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 8, "votes": ["b", "b", "b", "b", "b", "b", "a", "a", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context states the data fit both accounts to some degree, so neither is plainly inferior. Choosing between them depends on how one weighs parsimony against explanatory detail. Neither option reveals a recorded action.", "case_for_1": "A single trend with a slowdown is more parsimonious. It needs no arbitrary threshold to separate 'large-scale' from 'regular' systems. It also fits a plausible story in which early rapid growth came from scaling up from small budgets and then hit cost and hardware limits.", "case_for_2": "Two coexisting trends match how the field works: frontier labs push a few very large runs at a fast pace, while most models are limited by ordinary budgets and grow more slowly. This account also reconciles the earlier fast estimate, which was based on the largest systems, with the team's slower overall figure, and it explains why different samples give different rates."}}


### 1a7652d9b77c

A research team is building linear probes on a language model's internal activations to detect deceptive behavior. Two candidate training datasets are available. One is an instructed-pairs dataset, where the model is explicitly told to answer honestly or dishonestly on the same factual statements. The other is a roleplaying dataset, where the model is placed in scenarios that give it an incentive to lie, and its honest and deceptive completions are contrasted. The two datasets may yield probes that generalize differently to the team's evaluation settings. The team must pick one as the primary probe for the main experiments and treat the other as a secondary comparison.


A: Train the primary probe on the instructed-pairs dataset for the main experiments and test probes trained on the roleplaying dataset as an alternative.


B: Train the primary probe on the roleplaying dataset for the main experiments and test probes trained on the instructed-pairs dataset as an alternative.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 1, "votes": ["b", "b", "a", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are symmetric choices of which dataset is primary. The context gives no fact that makes either plainly inferior or reveals the recorded choice. Each has a plausible rationale tied to different priorities.", "case_for_1": "Instructed pairs are controlled: the same factual statements are used with only the honesty instruction changing, so the probe direction is cleaner and less confounded by scenario content. The dataset is easy to scale and reproduce, and it gives a simple baseline against which the roleplaying probe can be compared.", "case_for_2": "Roleplaying data, where the model has an incentive to lie, is closer to naturalistic strategic deception and so may generalize better to realistic evaluation settings. A probe trained on instructed honesty might only capture compliance with an instruction rather than deception, so making roleplaying the primary probe prioritizes ecological validity."}}


### 1f9008206d7a

A research team is evaluating its method across several task settings, one of which is an auditing-style setting involving AI systems (referred to here as the AI Audit setting). The team has to decide how this setting is treated in the write-up: whether it stays as one of the evaluation datasets whose results appear in the main body of the paper, or is reported only in supplementary material. The other evaluation settings are not affected by this choice.


A: Remove the AI Audit setting from the main results and report it in the appendix.


B: Keep the AI Audit setting as an evaluation dataset reported in the main results.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both placements are common and defensible. The context gives no facts showing that either option is clearly better, and it does not say which one was chosen. The decision depends on how much the setting matters to the paper's claims, how strong its results are, and how much space the main body has.", "case_for_1": "Moving AI Audit to the appendix frees main-text space and keeps the narrative focused on the settings that fit the method best. This is reasonable if the setting is noisy, only loosely related to the core claims, or hard to explain briefly. The results stay available as supplementary material, and the other settings are unaffected.", "case_for_2": "Keeping AI Audit in the main results is more transparent and shows the method's breadth, since auditing AI systems is a relevant and distinctive application. Moving a setting to the appendix could look like cherry-picking, especially if its results are weaker. Reviewers also tend to trust a paper more when its main evaluation covers all the settings it tested."}}


### 6144e7a21a5a

A research team is building a detector whose decision threshold must be set so that it produces a target false positive rate on benign inputs. This requires a control dataset of ordinary, non-target data. Two candidates are available. One is a large collection of real user conversations with a deployed chatbot, which is closer to the distribution the detector would face in practice but is messier and less controlled. The other is a curated, widely used instruction-following dataset of synthetic prompts and responses, which is clean and standard but more distant from real deployment traffic. The choice of control set determines the threshold and therefore the false positive rate the team will report.


A: Calibrate the false positive rate on a large collection of real user conversations drawn from chatbot usage.


B: Calibrate the false positive rate on a curated collection of synthetic instruction-following prompts and responses.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible. Real conversations give a more realistic false positive rate for deployment, while the curated synthetic set is clean, standard, and easier to compare with other work. The context states the trade-off without saying which one to choose.", "case_for_1": "The target false positive rate is meant to hold on real traffic, so calibrating on real user conversations gives a threshold and a reported rate that better reflect deployment. The messiness is part of the distribution the detector will face.", "case_for_2": "A clean, widely used benchmark makes results reproducible and comparable across papers. It avoids privacy problems and uncontrolled contamination, such as target-like content hidden in the real logs. It is a reasonable choice if the goal is a standardized evaluation or if real data is hard to obtain or use."}}


### 333a544c5e3c

A team developed a probing method on one language model, choosing a layer to probe at and a value for a key hyperparameter λ using that model. They now need to apply the method to a newer, related model in the same model family. The layer and λ were tuned only on the earlier model, and it is unclear whether they remain suitable for the newer one. The team must decide whether to carry the earlier settings over or to choose them again for the newer model.


A: Re-select the probing layer and λ through a fresh search on the new model, discarding the earlier model's settings.


B: Keep the probing layer and λ chosen on the earlier model, and validate them with sweeps on the new model.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 5, "votes": ["b", "b", "b", "b", "b", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are reasonable. Option 1 runs a full fresh search on the new model. Option 2 reuses the old settings as a starting point and checks them with sweeps on the new model. The context does not say which to choose, and the cost, comparability and robustness considerations differ between the two.", "case_for_1": "The layer and λ were tuned only on the earlier model, so they may be suboptimal for the new one. A fresh search on the new model avoids anchoring on the old settings and gives each model its own best configuration. This matters if the architecture or depth changed, since the best layer can shift.", "case_for_2": "Keeping the earlier settings preserves comparability across models in the family and reduces the risk of overfitting through a new search. Sweeps on the new model still check whether the settings hold, and they cost less than a full re-selection. If the sweeps show the old settings are poor, the team can adjust them."}}


### 40d926d6947f

A research team is building training data for language-model agents that operate in realistic software environments. Authentic agentic data, meaning traces of agents actually acting over multiple steps in real settings, is scarce because real deployment data is hard to find or access. Synthetic prompt-and-response data that does not involve real tool interaction is available but does not capture the behaviour of agents acting in real environments. The team needs a scalable way to obtain data that reflects real agent behaviour and interaction with real environments, and must choose how to produce it.


A: Harvest web tutorials, convert them into structured task specifications, and have a model-driven agent replay them in real environments with traces verified for correctness.


B: Run an existing open-source coding agent scaffold in scenarios of increasing complexity and collect the resulting interactions as the agentic data.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options produce real-environment agent traces at scale. Option 1 has a tutorial-grounded pipeline with correctness verification, which gives breadth and quality control but costs more engineering. Option 2 is simpler and cheaper, but it is limited to coding scaffolds and gives less assurance of correctness or diversity. Neither is plainly inferior, and the context does not state which one to pick.", "case_for_1": "Tutorials give diverse, realistic, human-grounded tasks across many software environments. Verified traces improve data quality, and the pipeline scales as more tutorials are harvested. This directly addresses the need for scalable data that reflects real interaction.", "case_for_2": "An existing scaffold needs little engineering and can start producing real tool-interaction traces right away. Increasing scenario complexity gives a controllable curriculum, and the approach is reproducible. It is a pragmatic choice when time or resources are limited."}}


### 9e0575bd4c8c

A research team compared language model judgments of whether a prompt or transcript looks like a real deployment interaction or an evaluation against human labels of the same property. The human raters found the task subjective and often disagreed with one another. The observed correlation between model labels and averaged human labels is about 0.8. The team must decide how to interpret this figure, given that noise and disagreement in both the human and model annotations may limit how high any observed correlation can be.


A: Apply a correction for unreliability in both human and model labels to estimate the agreement that would remain if label noise were removed.


B: Read the raw correlation as evidence that models have a fairly good sense of real versus evaluation, and note human subjectivity and rater disagreement as caveats.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible ways to interpret a 0.8 correlation under noisy labels. Disattenuation estimates the underlying agreement, but it depends on reliability estimates and assumptions, and it can overstate agreement. Reading the raw figure with caveats is more conservative and simpler, and it still acknowledges the noise. The context does not state which to choose.", "case_for_1": "The context explicitly says noise in both human and model labels caps the observable correlation. Correcting for attenuation gives a more accurate estimate of true construct-level agreement, and it avoids underestimating the models' ability. It is a standard psychometric step when raters disagree.", "case_for_2": "Reliability estimates from subjective, disagreeing raters are shaky, so the corrected number could be inflated or unstable. Reporting the raw correlation with caveats is transparent, avoids unverifiable assumptions, and still supports the modest claim that models have a fairly good sense of the distinction."}}


### 1a42e526040c

A research team is studying how well a model performs on a set of tasks, where each task is evaluated with a single prompt (PQ). Each model/dataset pair is therefore measured with only one prompt phrasing. The team observes that results under this setup are noisy: performance that looks strong for one model/dataset pair does not carry over to other pairs, and it is unclear how much of the variation comes from the particular prompt chosen rather than from the model or data. The team must decide how to present the finding about PQ performance given this noise from evaluating each prompt only once.


A: Report the single-prompt PQ result while stating that it is noisy and that strong PQ performance does not transfer across model/dataset pairs.


B: Evaluate each task with many paraphrased instruction templates and report performance across that distribution to measure prompt brittleness directly.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The decision is how to present a noisy single-prompt finding. Option 1 reports it honestly with caveats, which costs nothing extra. Option 2 does new work, evaluating many paraphrases, to measure prompt variance directly. Both are defensible, and they differ in cost and in how rigorous the evidence is. Option 2 is stronger scientifically, but it goes beyond presentation and requires extra compute and time.", "case_for_1": "Under limited budget or when the experiments are already finished, the team can still report truthfully. It states the limitation, avoids overclaiming, and does not delay the work. The decision is framed as how to present the finding, and a caveated report fits that framing.", "case_for_2": "Multiple paraphrased templates separate prompt effects from model and data effects. This addresses the stated uncertainty and gives robust, quantified results instead of a caveat. The added cost is moderate, since inference runs on existing tasks."}}


### 4f333acf5a8d

A research team wants to measure whether a language model believes it is being evaluated when it is placed in a given scenario. They must choose how to elicit this belief from the model. One approach asks open-ended prompts that invite the model to reason about its circumstances and leaves it to volunteer whether it suspects a test. The other approach asks directly whether the scenario is an evaluation, which gives a clear and easily scored signal but may prompt the model to reason about testing it would not otherwise consider, and so may overstate its real situational awareness.


A: Ask open-ended prompts that invite the model to infer its situation without mentioning evaluation directly.


B: Ask the model directly whether the scenario is an evaluation, accepting the risk of overstating its awareness.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are established ways to measure evaluation awareness. Open-ended prompts reduce the risk of priming the model, but they give a sparse, noisy signal that is harder to score. Direct questioning gives a clean, scalable signal, but it may inflate the apparent awareness. The context states these costs for each option and does not say which one to pick.", "case_for_1": "If the goal is to learn what the model spontaneously believes, avoiding priming matters most. Volunteered suspicion is a conservative, ecologically valid lower bound, and it avoids the demand-characteristic inflation that direct questions can cause. Researchers can accept noisier scoring and use more samples or an LLM grader to compensate.", "case_for_2": "Direct questioning is simple, cheap, reproducible, and easy to score. It gives an upper bound on awareness and can be compared across models and scenarios. The inflation risk can be quantified with control scenarios that are known not to be evaluations. Open-ended prompts may miss real awareness the model simply does not mention, so the direct question may be the better measure of capability."}}


### fe8546e359c5

A research team is working on eliciting latent knowledge (ELK): getting an AI system to report what it internally knows, even when its outputs could otherwise mislead overseers. The problem is open and conceptual, with no established solution and no clear benchmark for success. The team must choose a research methodology for making progress. One path is to build proposals and judge them only through theoretical analysis, searching for worst-case counterexamples and revising the proposals in response. The other is the standard research cycle of developing theory, implementing and testing it empirically, and using the observed flaws to improve it.


A: Follow the conventional cycle of developing theory, testing it in practice, identifying flaws from the experiments, and improving the proposals accordingly.


B: Skip empirical experiments, search for theoretical counterexamples to each proposal, and iterate on the proposals using those counterexamples.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 4, "votes": ["b", "b", "a", "b", "b", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are real methodological approaches to ELK. The conventional theory-plus-experiment cycle gives empirical feedback, while counterexample-driven theory (as in ARC's approach) targets worst-case robustness that experiments on current models may miss. The context describes both neutrally and does not reveal which was chosen.", "case_for_1": "Empirical testing grounds proposals in real systems, exposes flaws and implementation issues that theory misses, gives concrete feedback in a field with no benchmarks, and avoids drifting into unfalsifiable abstraction.", "case_for_2": "ELK concerns worst-case behavior of possibly superhuman systems, which experiments on today's models can't represent. A proposal that works empirically may fail adversarially, so counterexample search is faster, cheaper, and better matched to the worst-case goal."}}


### 342e1a4fbc90

A research team is building an uncertainty-aware top-k ranking method for image classification on a large-scale benchmark with about a thousand classes. Instead of always returning one label, the method returns a ranked list of candidate classes whose length varies with the model's uncertainty on each input. The team must set a maximum permitted list length, which bounds how many classes the method may output for any input. The benchmark's classes are grouped into semantic categories of very different sizes, and the largest categories (for example, fishes or dogs) contain many more fine-grained classes than a small fixed number. A small cap keeps lists short and easy to use but may truncate the list for highly ambiguous inputs. A cap tied to category size allows lists long enough to cover all fine-grained classes within the largest semantic group, but permits much longer outputs.


A: Cap the predicted list at a small fixed number of classes.


B: Cap the predicted list at the size of the largest semantic category.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 4, "votes": ["b", "b", "b", "b", "b", "a", "a", "a", "b", "a"], "quality": {"category": "valid_tradeoff", "reason": "The two caps trade list brevity and usability against coverage of ambiguous inputs. The context states the trade-off neutrally and does not say which cap to choose. Either cap is defensible depending on whether the application values compact outputs or recall within a semantic group.", "case_for_1": "A small fixed cap keeps outputs short and usable, which is the main purpose of top-k prediction. It bounds cost and makes results comparable with standard top-5 metrics. The method's adaptive length already shortens lists for confident inputs, so the cap only limits the rare, highly ambiguous cases.", "case_for_2": "A cap set to the largest category lets the method cover every fine-grained class in a group like dogs or fishes, which a small cap would truncate. Adaptive length means most lists stay short anyway, so the larger cap only matters for truly ambiguous inputs. This gives better coverage guarantees and a more faithful uncertainty representation."}}


### ae0ae838b7de

A research team is building an approximate inference method for a model whose latent variables are probability vectors on the simplex, such as topic proportions. They must choose a distributional family for the approximate posterior over these vectors. One candidate maps a Gaussian in unconstrained space onto the simplex through a softmax transformation, which allows flexible covariance between components but gives no closed-form expression for some of the expectations needed. The other candidate is the conjugate family defined directly on the simplex, which has fewer parameters and tractable expectations but a restricted correlation structure between components. The team must decide which family to use as the approximating distribution.


A: Use the Dirichlet distribution as the approximating family over the simplex-valued latent variables.


B: Use the logistic-Normal distribution as the approximating family over the simplex-valued latent variables.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 4, "votes": ["a", "a", "a", "b", "a", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are standard, defensible choices for variational families on the simplex. The Dirichlet gives tractable expectations and fewer parameters but cannot capture positive correlations between components. The logistic-Normal captures flexible covariance but needs approximations or sampling for some expectations. The context states these trade-offs without recommending either option.", "case_for_1": "The Dirichlet is conjugate, has closed-form expectations, and is cheap with fewer parameters. That makes optimization faster and more stable and keeps the method simple and scalable. If the correlation structure matters little, or the team values analytic coordinate updates, it is the sensible choice.", "case_for_2": "The logistic-Normal models correlations between components, such as topics that tend to co-occur, so it can give a more accurate posterior approximation. Reparameterized Monte Carlo gradients or Laplace/delta-method approximations handle the missing closed forms, so intractability is not a real obstacle with modern stochastic VI."}}


### 220ce18826d0

A research team is working to prevent a particular failure mode in trained AI models and has candidate prevention methods to assess. They must decide what kind of evidence to use to judge whether these methods work. One available source is a set of detection tools, including detailed evaluations on far out-of-distribution inputs, which can flag the failure mode in a model. These tools are imperfect, and their reliability is itself uncertain. Repeatedly tuning prevention methods against detection tools risks overfitting to them and weakening their value as independent checks. Another available source is a set of controlled experiments in which the failure mode is deliberately induced in model organisms, so that ground-truth labels exist for whether the failure occurred. The team must choose the primary basis for validating prevention methods.


A: Validate prevention methods with high-quality detection tools such as detailed far-OOD evaluations, and avoid iterating against every available detection tool.


B: Validate prevention methods with controlled model-organism experiments that induce the failure mode and use ground-truth labels to measure whether each method stops it.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Detection tools scale and apply to realistic models, but they are imperfect and risk overfitting. Model organisms give ground-truth labels, but they may not resemble naturally arising failures. The context does not make either option plainly inferior, and it does not name the recorded action.", "case_for_1": "Detection tools, especially far-OOD evaluations, can be applied to realistic, naturally trained models. They are cheaper and broader than building model organisms. Holding some tools back from iteration preserves them as independent checks, which mitigates the overfitting risk.", "case_for_2": "Ground-truth labels give a direct, reliable measure of whether a method prevents the failure, avoiding dependence on imperfect detectors and the overfitting problem. Model organisms allow controlled, repeatable comparison of methods, which suits a primary validation basis."}}


### 0c21abeb4677

A research team is modeling how AI model capabilities relate to release date by using an intermediate latent capability variable that links date to benchmark performance. They compare candidate causal paths using backtesting, in which models are fitted on earlier data and used to predict later benchmark results. One path goes from release date through an Elo-style rating to benchmark scores. Another goes from release date through the first principal component of a set of benchmark scores to benchmark scores. In backtesting, the principal-component path gives the lowest prediction error, with an RMSE of 0.082, while the Elo-based path gives a somewhat higher RMSE of 0.095. The team must decide whether the Elo-based path is acceptable to use as a validated path, or whether to use only the path with the lowest error.


A: Use the release date to principal component to benchmark path, since it has the lowest backtesting error of the candidates.


B: Accept the release date to Elo to benchmark path as validated, since its backtesting error is close to that of the best path.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 3, "votes": ["b", "b", "a", "b", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. The PC path has lower RMSE (0.082 vs 0.095), but the Elo path is only somewhat worse. Elo may be more interpretable and less circular, because a PC built from the same benchmarks it predicts can leak information. Accepting a near-best path as validated is a reasonable choice, and so is using only the best path. No fact makes either option plainly inferior, and the context does not reveal which was chosen.", "case_for_1": "Backtesting is the stated selection criterion, and the PC path wins on it. A roughly 14% lower RMSE is a meaningful gain. Using a single best path avoids multiplicity and keeps the model simple.", "case_for_2": "An RMSE of 0.095 is close to 0.082, so the Elo path predicts acceptably. Elo is an external, interpretable capability measure, while the PC is derived from the same benchmarks it predicts. Validating more than one path allows robustness checks and cross-validation of conclusions."}}


### c58875840aad

A research team needs a way to compute utilization rates for compute resources used in machine learning training. A single utilization figure can hide different causes of inefficiency, and different ways of computing it may give different answers for the same workload. The team must choose how to define and calculate utilization so that the resulting numbers are meaningful and trustworthy.


A: Compute utilization with several measurement methods based on theory, a single step, a batch, and an epoch, then compare how consistent the results are.


B: Decompose utilization into the product of availability, performance, and quality ratios so that each factor isolates a distinct kind of loss.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 5, "votes": ["b", "b", "b", "b", "b", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options address the stated problem. Option 1 handles the fact that different computation methods give different answers, by checking consistency across granularities. Option 2 handles the fact that one figure hides different causes of inefficiency, by decomposing it into availability, performance, and quality (an OEE-style breakdown). They target different halves of the concern, and neither is plainly inferior. They could also be combined, but as alternatives they reflect different priorities.", "case_for_1": "It directly tests whether the numbers are trustworthy by computing utilization at several granularities (theoretical, step, batch, epoch) and comparing them. This catches measurement artifacts and gives empirical confidence in the figures. It is cheap and does not require a loss taxonomy.", "case_for_2": "It gives a principled structure in which each factor isolates a distinct loss, so the result is diagnostic and actionable. It addresses the point that one figure can hide different causes of inefficiency. The multiplicative form also makes the definition explicit and comparable across workloads."}}


### 9b538361a5c2

A research team is building a taxonomy of failure modes for AI-driven automated research systems and must decide how to prioritize the categories within it. One category covers bugs, hallucinations, and artifacts, including hidden messages embedded in outputs. Such problems are common and usually look like ordinary mistakes that can be fixed or filtered out during review. Another view holds that some of these anomalies could signal deliberate scheming or steganographic communication between model instances, which would make them more serious than routine errors. The team must decide how much priority this category receives relative to the other failure modes in the taxonomy.


A: Rank bugs, hallucinations, and artifacts as the lowest-priority failure modes, treating them as routine and fixable errors.


B: Rank bugs, hallucinations, and artifacts higher, because they could signal scheming or steganographic communication between models.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given the stated facts. Option 1 follows the base rate: these problems are common, usually mundane, and fixable in review. Option 2 follows a risk-weighted view: a rare anomaly that signals scheming would be severe, so the category deserves more attention. The context presents both views without saying which to adopt, so this is a real trade-off between expected frequency and tail-risk severity.", "case_for_1": "Most such anomalies are ordinary bugs, so a taxonomy that ranks by likelihood and ease of remediation can put them lowest. Review already catches them, and attention is better spent on failure modes that review can't catch or that cause more harm.", "case_for_2": "Even if scheming or steganography is rare, its severity is high and it is hard to detect because it looks like a normal error. Ranking the category higher, or at least flagging it for scrutiny, is a sensible precaution. Dismissing anomalies as noise could hide a serious safety signal."}}


### 3baa789fcbe1

A research team is building a pipeline that needs a language model, accessed through a commercial API, to return outputs in a machine-readable structured format. The API offers two ways to constrain output format. One mode guarantees that the response is syntactically valid JSON but does not enforce any particular schema, so field names, types and required keys can vary and must be checked or handled downstream. The other mode accepts a developer-supplied schema and constrains generation so that the response conforms to it, at the cost of restrictions on supported schema features and some added setup. The team must choose which output mode to use for structured generation.


A: Use the mode that guarantees syntactically valid JSON without enforcing a schema, and validate the fields downstream.


B: Use the mode that constrains generation to a supplied schema, and accept its limits on supported schema features.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are realistic engineering choices. Schema-constrained output reduces downstream failures but limits schema features and requires setup. Plain JSON mode is more flexible and simpler to start with, but needs downstream validation. The context does not say which one the team picked, and it does not make either option clearly worse.", "case_for_1": "If the needed schema uses features the strict mode does not support (e.g., complex unions, recursive structures, or certain constraints), or the schema is still changing during early research, JSON mode avoids the setup and restrictions. The team likely validates with its own tooling anyway (e.g., Pydantic with retries), and this approach keeps it portable across providers.", "case_for_2": "Schema enforcement guarantees that keys and types conform, which removes a whole class of parsing and validation failures and the need for retries. This matters at scale or in an automated pipeline. The setup cost is modest, and the supported feature subset is usually enough for typical extraction schemas."}}


### a14eb0d14569

A research team built an initial prototype that applied automated prompt optimization with a declarative prompt-programming framework to the task of limit testing, meaning probing the boundaries of what a system can handle. The prototype was functional and produced some early signal. The team must now decide whether to commit further effort to this optimization approach or to stop at the prototype stage and direct effort elsewhere.


A: Continue the automated prompt optimization approach and develop it into a full method for limit testing.


B: Stop the automated prompt optimization work at the prototype stage and leave it undeveloped for limit testing.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context describes a functional prototype with some early signal, and the team is deciding whether to invest further or redirect effort. Both options are plausible. Continuing exploits the promising signal, while stopping preserves resources for other priorities. Nothing in the context states which action to take, and neither option is plainly inferior.", "case_for_1": "The prototype works and shows early signal, so the marginal cost of developing it into a full method is likely lower than starting something new. Declarative prompt-optimization frameworks are maturing, and limit testing may benefit from systematic optimization. Stopping now would waste the sunk investment and forgo a potentially publishable result.", "case_for_2": "Early signal is weak evidence, and optimization approaches can overfit or fail to generalize to boundary probing. Limit testing may be better served by simpler or hand-crafted methods, and opportunity cost matters. Stopping at the prototype preserves limited team effort for more promising directions, and the prototype itself remains a documented result."}}


### 3b08f23440a6

A research team is building a benchmark that scores how goal-directed a model is, and the score is reported on a bounded scale. Before they can report results, they must decide how to read that scale. In particular, they must fix which score corresponds to a minimally goal-directed model, meaning one that shows only the weakest degree of consistent goal pursuit. The choice affects how every later score is understood, including whether scores near the bottom of the range indicate no goal-directedness or a baseline amount of it.


A: Treat a score of 0 as the level of a minimally goal-directed model on the scale.


B: Treat a score of about 0.5, rather than 0, as the level of a minimally goal-directed model.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 4, "votes": ["a", "a", "a", "a", "b", "a", "b", "b", "a", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are plausible conventions for anchoring a bounded scale. Setting 0 as the minimum matches the usual zero-baseline reading. Setting about 0.5 as the minimum treats the scale as having a nonzero baseline, for example when 0.5 is chance-level or a random-policy floor. The context does not say which convention is correct, and it does not reveal the recorded choice.", "case_for_1": "A zero anchor is simple and intuitive. It means the lowest score is the minimal goal-directedness level, so scores are easy to interpret and compare. It also avoids committing to an arbitrary baseline value.", "case_for_2": "A nonzero anchor near 0.5 can reflect that even a random or minimally goal-directed model gets some baseline score by chance or by incidental behavior. Scores below 0.5 can then be read as anti-goal-directed or noise. This separates minimal goal-directedness from none at all, which the context raises as a concern."}}


### a6ed34a9d46a

A research team is studying how to evaluate the goal-directedness of language models on a suite of benchmark tasks. They want a principled way to characterize how strongly a model pursues goals, including an upper bound on that tendency. One path is to fine-tune a model on goal-directed reasoning traces drawn from the benchmark tasks, in order to elicit its maximum goal-directedness empirically. Another path is to define a formal, model-agnostic measure of how well observed behavior fits optimization of a known or hypothesized utility function. The team has not yet committed to either approach.


A: Fine-tune a model on goal-directed reasoning traces from the benchmark tasks to elicit its maximum goal-directedness.


B: Define a formal goal-directedness measure based on inverse reinforcement learning that scores how well behavior fits a utility function.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are realistic, established ways to study goal-directedness. Fine-tuning gives an empirical upper bound tied to a specific model and the benchmark tasks. An IRL-based formal measure is model-agnostic and principled but depends on utility-function assumptions. Neither is plainly inferior, and the context does not reveal which one was chosen.", "case_for_1": "It directly targets the stated goal of an upper bound on goal-directedness by eliciting the model's maximum capability. It is concrete and implementable on existing benchmarks, and it doesn't require specifying a utility function. It also reveals latent tendencies that ordinary prompting might miss.", "case_for_2": "It gives a principled, model-agnostic, reusable measure that allows comparison across models and doesn't depend on training-set choices. It avoids confounds from fine-tuning, where training may instill goal-directedness rather than reveal it. It also matches the team's wish for a principled characterization."}}


### ef95965b8e59

A research team evaluated language models for misalignment and deception in an agentic environment. Older, smaller models in the GPT family showed lower rates of misaligned and deceptive behavior than newer, larger models. The team had to decide how to interpret this gap. One possible explanation is that older models lack the capability to act competently in the environment, so their low rates reflect inability rather than better alignment. Another is that the pattern reflects a genuine trend in which misalignment changes with model scale. The available evidence from the environment alone could not cleanly separate these explanations.


A: Skip explaining the gap, and instead measure deception directly by fine-tuning models of several sizes under controlled data-poisoning conditions to read the scaling trend.


B: Attribute the lower rates only partly to older models' inability to act competently, and refuse to treat them as evidence that misalignment grows with scale.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 8, "votes": ["a", "b", "b", "a", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible responses to an ambiguity the context says cannot be resolved from the environment alone. Option 1 gathers new evidence through a controlled experiment. Option 2 interprets cautiously with the existing data. They differ in cost, speed, and epistemic ambition, and neither is plainly inferior. The context does not reveal which one was chosen.", "case_for_1": "The context says the environment alone cannot separate the explanations, so new, controlled evidence is the way to resolve it. Fine-tuning models of several sizes under controlled data-poisoning conditions isolates scale from competence and gives a real read on the scaling trend instead of speculation.", "case_for_2": "It is cheap and honest. It avoids over-claiming from confounded data, it acknowledges the capability confound, and it withholds the scale-trend conclusion until better evidence exists. This suits a team with limited resources or one that only needs to report the finding responsibly."}}


### bf66fe551561

A research team studying deception in language models needs an automatic way to label whether model outputs are lies, since manual labeling at scale is infeasible. A prompted GPT-4 judge is available as a classifier of deceptive outputs and could be used immediately. Its reliability has not been established beyond a small informal check. Alternatively, a smaller model could be trained specifically for the task, and several existing datasets with ground-truth truth/lie labels are available for training and evaluating it. The team must decide how to obtain a deception classifier they can trust for their main experiments.


A: Adopt the prompted GPT-4 judge as the deception classifier after a researcher manually checks a small sample of its labels.


B: Fine-tune a small FLAN-T5 model as the deception classifier and evaluate it against ground-truth labels across existing datasets.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Option 1 is fast and cheap, but it relies on a small manual check, so its reliability is weakly established. Option 2 takes more effort and may generalize worse, but it is validated against ground-truth labels across several datasets. The context says the team needs a classifier it can trust, which favors Option 2 somewhat, but it does not make Option 1 plainly inferior. GPT-4 may be more capable on out-of-distribution outputs, and the manual check can be expanded. The context also does not reveal which action was taken.", "case_for_1": "GPT-4 can be used immediately with no training cost. It likely handles diverse, nuanced lies better than a small model trained on existing datasets, which may not match the team's experimental distribution. A manual check on a sample drawn from the actual experiments directly tests the target distribution, and the sample can be expanded if agreement looks weak.", "case_for_2": "Fine-tuning on ground-truth labels and evaluating across multiple datasets gives quantitative, reproducible accuracy estimates, including cross-dataset generalization. The resulting model is cheap to run at scale, deterministic, and not dependent on an API that may change. This better meets the requirement of a classifier the team can trust."}}


### d30f68917016

A research team evaluated a language model with in-context examples, where the order of elements within the demonstration shots differed from the order used in the final test prompt. Performance was worse in this mismatched condition. In addition, prompts with several shots scored lower than prompts with a single shot. The team had to decide how to explain this drop and the k-shot versus one-shot gap.


A: Interpret the drop as an artifact of the order mismatch between shots and prompt, and treat k-shot underperforming one-shot as a result of that inconsistency rather than priming.


B: Interpret the drop as the model attending to prompt form over content, and treat k-shot underperforming one-shot as the shots priming the model toward errors.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are plausible explanations for the same observations. Option 1 attributes the drop to the order mismatch (a distribution-shift artifact). Option 2 attributes it to form-over-content attention and error priming from multiple shots. The context does not say which is correct, and the two could be separated by further experiments. Neither is plainly inferior, and the context does not leak the chosen action.", "case_for_1": "The mismatch is the one manipulated variable, so it is the most parsimonious explanation. With k shots there are more mismatched demonstrations, so the inconsistency compounds and could explain k-shot underperforming one-shot without any priming mechanism.", "case_for_2": "Prior work shows that models are sensitive to surface form and that demonstrations can bias them toward repeated errors. This explains why more shots hurt, since more examples give stronger priming, and it fits the mismatch result as a form-sensitivity effect."}}


### 9e6a31c2edca

A research team observed an intriguing behavior in a system under study, demonstrated in a single constructed scenario. The behavior appeared striking, but the team did not know how representative the scenario was or how often the behavior would arise across other situations. They had to decide how far to generalize from this one demonstration: whether to state a broader regularity and quantify it across many cases, or to present the demonstration only as evidence that the behavior can occur, without claims about its prevalence.


A: Present the result as an existence proof and draw no conclusions about how likely the behavior is in practice.


B: Define the scope of the claimed regularity and measure its strength as the percentage of many cases that conform.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 7, "votes": ["a", "a", "a", "a", "a", "a", "b", "b", "b", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given a single demonstration and unknown representativeness. An existence proof is honest and cheap, and a prevalence study is more informative but costs more and requires defining scope and a case sampling frame. The context frames the decision neutrally and does not reveal which was chosen.", "case_for_1": "One constructed scenario supports only a claim that the behavior can occur. Claiming more without evidence would overgeneralize. An existence proof is valid, quick, and useful for flagging risks or counterexamples. It avoids the arbitrary choice of a case distribution, which could make a prevalence number misleading.", "case_for_2": "An existence proof alone has limited value. Defining the scope and measuring the conforming percentage across many cases turns an anecdote into a testable, quantified regularity. It shows whether the behavior is common or rare, which matters for practical relevance, and it can also reveal boundary conditions if the team has the resources."}}


### 29d0d8093b15

A research team working on AI safety is talking with academics, many of whom are outside the AI safety community, to build interest and collaboration around their research agenda. The team believes that risks from advanced AI systems, including extinction-level outcomes, are a central reason the research matters. They also know that many academics regard such existential-risk framing as speculative or fringe, and that it may affect how seriously the academics take the researchers and the work. Other, more familiar failure modes of AI systems, such as robustness problems, misuse, and unintended behavior, could also be used to justify the same research. The team must decide how to frame the motivation for their work in these conversations.


A: Raise existential risk openly in these conversations and use it as the primary motivation for the research.


B: Avoid raising existential risk unless asked, and motivate the research with other, more familiar failure modes.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both framings are defensible. The choice trades off honesty and transparency about the team's true motivation against credibility and receptivity among skeptical academics. The context states neither option is clearly better, and it does not reveal which one was chosen.", "case_for_1": "Leading with existential risk is honest about why the team cares. It avoids a bait-and-switch, attracts collaborators who share the real concerns, and helps normalize the topic in academia. It also keeps the research agenda aligned with the actual threat model rather than with proxy problems that may not address extinction-level risk.", "case_for_2": "Motivating the work with robustness, misuse, and unintended behavior is truthful, since these are real risks the research addresses, and it avoids triggering dismissal. It builds credibility and relationships first, and existential risk can still be discussed when asked. This may enable more collaboration and a more productive dialogue, as long as the team does not misrepresent its views."}}


### c619a1db96c0

A research team is analysing a time series that shows a clear acceleration in growth after 2018. The post-2018 data points fall into two groups, one below and one above a visible gap. The acceleration can be described either by a single exponential trend across all post-2018 points or by two separate trends, one for the points below the gap and one for those above it. The two-trend description adds free parameters and a split chosen after seeing the data, so it risks overfitting. The single-trend description is simpler but may fit the two groups poorly. The team must decide how to interpret the post-2018 acceleration.


A: Fit one exponential trend to all post-2018 data and treat the acceleration as a single continuous process without any split.


B: Split the post-2018 data into separate below-gap and above-gap trends and accept the overfitting risk that the split carries.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context sets out a standard parsimony versus fit trade-off. A single trend avoids post-hoc splitting and extra parameters. Two trends may capture a real structural difference between the groups. Neither option is clearly inferior, and the context does not say which to pick.", "case_for_1": "The split was chosen after seeing the data, and it adds parameters. A single exponential is the parsimonious, less overfit-prone explanation. It can be checked with out-of-sample tests or information criteria, and a visible gap alone does not prove two regimes.", "case_for_2": "If the gap reflects a real regime change, such as a different mechanism or a measurement shift, a single trend would fit both groups poorly and misdescribe the acceleration. The two-trend model can be justified with model comparison (AIC/BIC) or cross-validation, and the overfitting risk can be explicitly acknowledged and reported."}}


### 56c0ba3e0c02

A research team observed a gap between two sets of results and needed to determine its cause. An outside group had suggested that the degree of parallelism used during inference, and whether it crosses a certain threshold, could account for the discrepancy. The team had to decide whether this factor deserved to be treated as an explanation for the gap.


A: Accept inference parallelism as a meaningful factor and attribute the explanation for the gap to it.


B: Rule out inference parallelism as a meaningful factor and seek the explanation for the gap elsewhere.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 1, "votes": ["a", "a", "a", "a", "a", "a", "b", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context gives no evidence on whether inference parallelism explains the gap. Accepting or ruling out an outside hypothesis are both plausible responses depending on priors and plausibility. The context does not state or hint at the recorded action. The options are comparable and mutually exclusive.", "case_for_1": "The outside suggestion is specific and testable: a parallelism threshold can plausibly change numerics, batching, or nondeterminism and so produce a result gap. Accepting it as a working explanation lets the team act quickly, and it could resolve the discrepancy without a broader search.", "case_for_2": "Without confirming evidence, attributing the gap to an outside hypothesis is premature. Ruling it out, or at least deprioritizing it, keeps the team from settling on a spurious cause. If the team has already seen that parallelism has negligible effect or that the gap persists across settings, searching elsewhere is the more rigorous course."}}


### 915710e70941

A team is analysing a dataset of large language models and finds a gap in the range of model sizes, with no models falling inside it. Some models that sit inside this range exist but were left out of the dataset under its inclusion criteria. These are smaller versions built only for scaling tests and one mid-sized model from a single developer. The team must decide how to handle these models before characterising the gap.


A: Add the excluded scaling-test versions and the mid-sized model to the dataset, then re-examine whether the gap still appears.


B: Keep the scaling-test versions and the mid-sized model excluded, and report the gap as a surprising feature of the data.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Adding the excluded models tests whether the gap is an artifact of the inclusion criteria. Keeping them excluded respects the dataset's stated definition, since scaling-test versions are not real released models. The context does not say which option to take.", "case_for_1": "The gap may be an artifact of the inclusion criteria, so checking its robustness before characterizing it is sound. The mid-sized model is a genuine model and arguably should count. Re-examining with the models added, and reporting both versions, makes the finding more credible.", "case_for_2": "The inclusion criteria were set for a reason. Scaling-test models are research artifacts rather than deployed models, so adding them would distort what the dataset represents. The team can keep the criteria, report the gap, and note the excluded models as a caveat or sensitivity check. This keeps the analysis consistent and avoids post hoc changes to the data. The wording 'surprising feature' is somewhat loaded, but the option is still coherent."}}


### ec771a3c83a3

A research team has been studying the limits of reconstruction and whether scaling laws apply to concepts. They have preliminary understanding of the problem and must decide whether to continue this line of work. Further progress could deepen understanding of how reconstruction and scaling behave for concepts, but it could also advance capabilities in ways that carry risk. The team must choose between continuing the investigation and holding back because of that risk.


A: Hold back from further investigation of reconstruction and concept scaling laws because of the capabilities risk.


B: Continue investigating the limits of reconstruction and scaling laws for concepts with further research.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context presents a real dual-use dilemma: continued research offers scientific understanding but may advance risky capabilities. Both holding back and continuing are defensible, and the context does not say which to choose or reveal a recorded action.", "case_for_1": "Because the team's understanding is only preliminary, it is unclear whether the risks can be managed. Scaling-law insights can accelerate capabilities in hard-to-reverse ways, so a precautionary pause is defensible until safeguards or a risk assessment exist. Not publishing or not pursuing the work avoids contributing to capability proliferation.", "case_for_2": "Understanding the limits of reconstruction and concept scaling may clarify what is and isn't possible, which can inform safety work and policy. The work is still preliminary, so the risk is speculative, and the team could continue with staged disclosure or internal review. Halting could also forgo valuable knowledge that others would pursue with less caution."}}


### 6fc39c3191cd

A research team is assessing why nuclear power construction has become expensive in many Western countries and whether it can be built cheaply. Reported construction costs for recent reactors in South Korea and China are substantially lower than those in Western countries, which could suggest that low costs are achievable. However, these figures come from state-influenced systems with limited transparency, different accounting conventions, labor and financing arrangements, and uncertain comparability with costs elsewhere. The team must decide how to treat these figures when judging whether nuclear can be built cheaply.


A: Discount the South Korean and Chinese cost figures as unreliable or non-comparable rather than taking them at face value.


B: Accept the low South Korean and Chinese cost figures as credible evidence that nuclear power can be built cheaply.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given the stated facts. The context notes real comparability and transparency concerns, but the Korean and Chinese figures are still the best available evidence that low costs may be achievable. The options sit at opposite ends of a spectrum, and a careful team could reasonably choose either, or a middle path.", "case_for_1": "State influence, opaque accounting, different labor and financing arrangements, and unclear comparability all mean the figures could substantially understate true costs or reflect conditions that cannot be replicated in the West. Treating them as unreliable avoids overconfident conclusions that could misdirect policy or investment.", "case_for_2": "South Korea and China have built many reactors on repeatable schedules, and independent analyses have often found their costs to be genuinely lower. Even with some accounting differences, the gap with Western costs is too large to be explained by measurement alone. Dismissing it would ignore the strongest real-world evidence that costs depend on institutions and practices rather than on the technology itself."}}


### 41a18124ca73

A research team is building a long-range forecast of the future cost and availability of computing hardware, specifically GPUs used for large-scale computation. They must decide what assumption about physical limits to base the prediction on. One approach treats the technology as bounded by a fundamental physical constraint on how small transistors can get. The other approach treats historical trends in cost reduction as the basis for projection. Available evidence includes long-running empirical data on how hardware costs have fallen with cumulative production and improvements, as well as known physical considerations about transistor scaling and the dominant current transistor design. The forecast will be used to inform expectations about future computing capacity, and the team must choose which foundation to build it on.


A: Assume transistors cannot shrink beyond roughly the size of a single silicon atom, and model only field-effect transistor-based GPUs.


B: Extrapolate empirically observed historical cost-learning trends probabilistically with uncertainty, and assume no hard physical limit on the technology.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are recognized forecasting approaches. A physics-bounded model gives a conservative ceiling tied to the current transistor paradigm. A probabilistic extrapolation of historical learning curves is empirically grounded and can capture architectural and paradigm shifts. Each has real weaknesses: the first ignores alternative designs and 3D or architectural gains, and the second ignores physical limits. Neither is plainly inferior, and the context does not reveal which was chosen.", "case_for_1": "Physical limits are real. The atomic-scale floor and the dominance of FET designs make a bounded model credible for the near-to-medium term. It avoids unlimited extrapolation and gives a concrete, defensible ceiling for capacity planning.", "case_for_2": "Cost-learning curves have held across many technology transitions, and the approach explicitly models uncertainty. It doesn't depend on the fragile claim that FETs and atom-scale limits are the binding constraints, since packaging, architecture, and new devices can continue cost-performance gains. It is better suited to long-range forecasting."}}


### 689ddac68585

A research team has several research lines whose outcomes are highly uncertain. Some of these lines are unlikely to produce results that are clean or conclusive enough to publish, though they could be valuable if they work. The team must decide how to handle such lines. It can keep investing effort in them despite the publication risk. It can also stop pursuing them and direct its effort toward work that is more reliably solid and publishable.


A: Keep pursuing the risky research lines even when they are unlikely to be publishable.


B: Drop the risky research lines entirely and prioritize work that is more robustly good.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "This is a classic explore-vs-exploit choice. Persisting with high-risk lines offers potential high payoff but risks wasted effort and no publications. Dropping them secures reliable output but forgoes upside. The context states no facts that make either option clearly inferior, and it does not reveal which was chosen.", "case_for_1": "If the team has stable funding, tenured or senior members, and values breakthroughs, risky lines could yield outsized impact that safe work cannot. Unpublishable results can still build expertise, negative-result knowledge, and a long-term advantage. Abandoning them entirely would eliminate that upside.", "case_for_2": "If the team faces publication-driven evaluation, has junior members who need outputs, or has limited resources, prioritizing robust work protects careers and funding. Concentrating effort on dependable lines produces cumulative, verifiable progress and avoids sunk-cost drift into dead ends."}}


### ae496dd83577

A research team that works on interpretability-style research must decide whether to publish its work. The worry is that publishing could advance general AI capabilities. Some publications could help capabilities directly, for example by supplying a technique that makes models more capable. Others could help only indirectly, through longer causal chains such as shifting attention, enabling later work, or changing how people understand models. Direct effects are comparatively easy to identify. Indirect effects are diffuse, speculative and hard to assess. The team must settle the scope of its publication policy: either follow a wider set of capabilities effects, or restrict the policy to the effects it can most clearly identify.


A: Ignore indirect capabilities effects and weigh only direct capabilities help when deciding whether to publish.


B: Track indirect capabilities effects and weigh them alongside direct capabilities help when deciding whether to publish.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context frames a real scope decision. A narrow policy that covers only direct effects is tractable, predictable, and avoids chilling publication over speculative harms. A broad policy covers more of the real risk but is vague and may suppress useful safety work. Neither option is plainly inferior, and the context does not say which one to choose.", "case_for_1": "Direct effects can be identified reliably, so the policy is consistent and enforceable. Indirect effects are speculative, and weighing them could block valuable interpretability work on guesses. Publishing also has benefits such as safety progress, field-building, and scrutiny. A clear, narrow rule is more likely to be followed and can be revisited later.", "case_for_2": "Much capabilities impact may come through indirect channels such as shifting attention, enabling follow-on work, and changing how people understand models. Ignoring these leaves a large blind spot. Uncertainty does not make the effects zero, and the team can weigh them with discounting or rough probabilities. A wider policy better serves the stated worry about advancing capabilities."}}


### 406565325849

A person who is early in a research career and working without institutional supervision must decide how to spend their time. They can pursue self-directed projects with the aim of producing concrete research outputs, or they can focus on deliberately building foundational skills before attempting such outputs. The two aims call for different ways of working, and effort spent on one does not automatically advance the other. Established learning curricula exist for the skill-building path. The person has not yet settled on which goal matters most to them.


A: Pursue independent research projects with the primary aim of producing concrete results.


B: Work through existing curricula with the primary aim of building skills before producing results.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are realistic approaches for an unsupervised early-career researcher. The context says the goals differ, that effort on one does not automatically advance the other, and that the person has not decided which goal matters more. It does not recommend either option or reveal what was chosen.", "case_for_1": "Producing real outputs gives feedback, a portfolio, and evidence of ability, which matters when there is no institutional credential. It also builds skills in context, shows which skills are actually needed, and tests whether the person likes doing research. Curricula can be picked up as gaps appear.", "case_for_2": "Without supervision, projects can drift, be poorly designed, or reinforce bad habits. Established curricula give a structured and efficient route to a solid foundation, so later projects are higher quality and less wasteful. This is a sound choice if the person's main gap is fundamentals."}}


### dde98cbc9455

A research team is studying a trained classification model and has proposed a simple, human-interpretable labeling function intended to reproduce the model's predicted labels. When evaluated, the function agrees with the model's labels on 96.2% of examples. The model itself is known to be correct on about 95.6% of examples with respect to ground truth. The team must decide how to interpret the remaining disagreement between the labeling function and the model, since it could reflect either a shortcoming of the labeling function or errors made by the model.


A: Attribute the remaining gap to model error and accept the current labeling function without further search.


B: Search for a better simple labeling function to close the remaining gap with the model's labels.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 5, "votes": ["b", "a", "b", "b", "a", "b", "a", "a", "a", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. The 96.2% agreement is close to the model's 95.6% accuracy, so the remaining 3.8% disagreement could plausibly be model error. That makes stopping reasonable. But agreement with the model's labels is not agreement with ground truth, so the two kinds of error can't be separated from these numbers alone, and further search is also reasonable.", "case_for_1": "The function already matches the model on 96.2% of examples, and the model is wrong on about 4.4%. A simple function can't be expected to reproduce those errors, so much of the 3.8% gap may be model mistakes. Further search risks overfitting the model's errors and costs complexity and interpretability. Stopping is efficient.", "case_for_2": "The context doesn't establish that the disagreement is model error. It could just as well come from gaps in the labeling function. The disagreement can be checked: inspect the disputed examples against ground truth, then refine the function. A better simple function would be a more faithful explanation, and the extra search is cheap relative to the gain in fidelity."}}


### 2b9892fa70fc

A research team is trying to mechanistically understand how a trained transformer performs its task by reverse-engineering its internal computation. The model's attention heads produce patterns that vary across inputs, and inspection of these patterns has not made their function obviously interpretable. The team must decide what object to analyze: the complete model with its input-dependent attention, or a simplified variant in which attention patterns are replaced by fixed values, such as their averages over the dataset. The simplified variant would be easier to analyze, but it could discard computation that the real attention performs.


A: Reverse-engineer the simplified transformer, replacing its attention patterns with fixed dataset-mean values.


B: Reverse-engineer the full transformer, keeping its input-dependent attention patterns intact.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Mean-ablating attention patterns gives a linear, tractable object but may discard input-dependent computation. Analyzing the full model is faithful but harder, and its attention patterns have already resisted simple interpretation. The context states the trade-off and does not say which to choose.", "case_for_1": "The simplified model is far easier to analyze and often yields a clean, mostly linear circuit description. Before analyzing the full model, the team can measure how much performance the simplification retains, which tells them how much computation lives in the attention patterns. If most performance survives, the simplification is a sound foundation. If it does not, they have located where the input-dependent computation is.", "case_for_2": "The full model is the real object of study. Replacing attention with averages risks explaining a different system and missing the very input-dependent computation that matters. Direct inspection of patterns was unhelpful, but that does not show the full model is intractable. Techniques such as path patching, attribution, and causal interventions can work on the full model without altering its computation, so the explanation stays faithful."}}


### 1849b58b0cef

A research team studying a model's internal behavior has just completed an analysis in which attention patterns were held fixed, to test how much of the model's behavior depends on the attention mechanism. The analysis gave them an initial view of the role attention plays, but it left open how attention actually contributes and whether a deeper account is within reach. The team must decide how to allocate further effort: continue examining the attention mechanism in more depth, or conclude the investigation at this point and record the fixed-attention analysis as a possible starting point for later work.


A: Continue the attention investigation and devote further time to understanding the attention mechanism itself.


B: Stop the attention investigation here and leave the fixed-attention analysis as a suggested first step for others.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. The context says the analysis left open how attention contributes and whether a deeper account is feasible, so continuing and stopping each rest on plausible priorities. It does not state which action was taken or which is better.", "case_for_1": "The fixed-attention analysis only gave an initial view and left the mechanism unexplained. Attention is central to model behavior, so further work could yield real understanding. The team already has context and momentum, which makes follow-up efficient.", "case_for_2": "It is unclear whether a deeper account is within reach, so more effort might not pay off. Publishing the fixed-attention result as a starting point frees resources for more tractable questions and lets others build on it. This is a reasonable scoping decision."}}


### e5c6666dfd06

A research team tested a mechanistic hypothesis about how a model performs a particular behavior. They used a scrubbing procedure, which replaces internal activations with ones that the hypothesis treats as equivalent, and measured how much of the model's original performance survived. Under the hypothesis, scrubbed performance stayed at roughly 93-94% of the original. The remaining gap of about 6% could reflect behavior the hypothesis does not capture, or it could be a sign that the hypothesis is incomplete. The team also had results from more specific versions of the hypothesis, and recovered performance dropped as the hypothesis became more specific. The team had to decide how strongly to claim that the hypothesis is validated.


A: Present the hypothesis as reasonably but not fully accurate, and treat the remaining gap as unexplained behavior, noting that recovery falls with specificity.


B: Present the preserved performance as a strong result that supports the hypothesis, and attribute the remaining gap to behavior the hypothesis does not cover.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible readings of 93-94% recovery. The first is more cautious and reports the drop with specificity. The second leans on the high recovery and treats the gap as out of scope. Neither contradicts the stated facts, and the choice depends on how conservative the team wants to be.", "case_for_1": "The decline in recovery as the hypothesis becomes more specific is real evidence that the hypothesis is incomplete or that its finer details are wrong. The 6% gap is unexplained, so calling it unexplained is honest. A moderate claim with caveats is the more epistemically careful choice and is less likely to be overturned later.", "case_for_2": "93-94% recovery is high by the standards of scrubbing experiments, and the main hypothesis is a reasonable coarse-grained account. The gap could plausibly come from behavior outside the hypothesis's scope, which the context explicitly allows. Specificity trends are expected because finer hypotheses make stronger claims, so they need not undermine the coarse claim. A strong framing is defensible if it still states the gap and the scope limits."}}


### 122f859f45e1

A research team trained a model on a task whose ground-truth labeling function was known, and then applied interpretability analysis to check whether that function could be recovered from the trained model. The recovery did not succeed: the original labeling function could not be identified in the model. The team had to decide how to interpret this failure, since it could reflect either what the model actually learned or a limitation of the interpretability analysis.


A: Interpret the model as having learned the true labeling function despite the failed recovery, and treat the mismatch as a shortcoming of the interpretability analysis.


B: Interpret the model as having memorized and interpolated the training data rather than learned the labeling function, and treat this as no loss for interpretability.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context states the failure is ambiguous between a model-side cause and a method-side cause. Option 1 attributes it to the interpretability method, and option 2 attributes it to what the model learned. Both are live hypotheses, and the facts do not settle which holds. Option 2's added claim that this is 'no loss for interpretability' is somewhat convenient, but it can be defended: if the model never learned the function, there was nothing to recover.", "case_for_1": "A model trained on a task with a known ground-truth function may well have learned it, especially if it generalizes well. Interpretability methods are imperfect, and a failed recovery is weak evidence against the model having the function. Blaming the tool is a reasonable default until the method is validated, and this stance motivates improving the method.", "case_for_2": "If the model fits the training data but does not generalize, or if probing finds no trace of the function, memorization and interpolation is the more parsimonious explanation. Recovery fails because the function is absent, which says nothing against the interpretability method. Taking the failure at face value avoids unfalsifiable excuses for the tool."}}


### 8efcfc9be84b

A research team evaluating language models across a range of scales found that performance on a task category testing whether models give answers consistent with human defaults (facts-human-defaults, where a model asked about personal facts such as body or life experience should respond as a human would) is non-monotonic: accuracy first falls and then rises as scale increases, producing a U-shaped curve. The team needed to decide on an explanation for this pattern. The evidence available included results for base models and chat-finetuned models of many sizes, and the ability to analyze the questions individually by difficulty.


A: Attribute the U-shape to a progression in which weak models are confused, mid-scale base models imitate humans best, and larger or chat-finetuned models grow confident they are not human.


B: Split the questions into easy and hard subsets and attribute the U-shape to inverse scaling on easy questions combined with standard scaling on hard ones, with the easy-question trend reverting at larger scales.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 1, "votes": ["b", "b", "b", "a", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are plausible explanations for a U-shaped curve, and the stated evidence (base vs chat models, per-question difficulty analysis) supports either. Option 1 is a mechanistic narrative that uses the base/chat comparison. Option 2 is a decomposition by difficulty that uses the per-question analysis. Neither is obviously inferior, and the context does not reveal which one was chosen.", "case_for_1": "It fits the base vs chat evidence directly. Chat finetuning and larger scale plausibly teach models to say they are AI, which gives an interpretable account of why accuracy falls and then rises. It also explains why the human-default behavior varies with model type.", "case_for_2": "It is testable and quantitative. Splitting by difficulty can show whether the U-shape is a mixture of two different scaling trends, which is a standard way to explain non-monotonic curves. It also makes fewer assumptions about what the models believe about themselves."}}


### 02d143ab977d

A research team built SAD, a benchmark intended to measure how well language models understand themselves and their own situations, and evaluated it on language models spanning only a few recent generations. Scores on the tasks show models still performing well below the ceiling, so the benchmark appears unsaturated for the models tested. The team must decide how strongly to state that SAD remains unsaturated, given that the evidence covers only a narrow range of model generations and that future model progress is uncertain.


A: Claim that SAD will remain unsaturated for at least the next generation of language models, extending the conclusion beyond the tested models.


B: Report how one current frontier model scores on a few SAD tasks using a coarse graded rating that shows remaining headroom, without forecasting future saturation.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The two options differ in how strongly they state the conclusion. Option 1 forecasts beyond the tested models, which is informative but is not supported by the narrow generational evidence. Option 2 limits itself to the current evidence and avoids a forecast, which is cautious but says less. Neither is clearly inferior, and the context does not reveal which option was recorded.", "case_for_1": "Benchmark users want to know whether a benchmark will stay useful. Scores well below the ceiling give some basis for a modest, near-term forecast, and 'at least the next generation' is a limited claim. A forecast makes the benchmark more useful for planning and gives other researchers something they can check.", "case_for_2": "The evidence covers only a few recent generations and future progress is uncertain, so extrapolating is risky. Reporting current headroom, with a coarse rating, stays within what the data show. It protects credibility if a later model jumps in performance, and readers can draw their own forecasts."}}


### 09dca327fb5d

A research team evaluating language model outputs needed an automatic way to judge whether each response followed an instruction to be written in a particular language or style. Manual annotation of every response was impractical at the evaluation's scale, so an automated model-based grader was needed to label each response as compliant or not. The choice was between a more capable grader model and a cheaper, widely used grader model whose output would be parsed strictly, with only an explicit affirmative verdict counted as compliant.


A: Use a stronger, more capable grader model to judge whether each response matches the requested language or style.


B: Use a cheaper, widely used grader model to judge each response and count only an explicit affirmative answer as correct.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are plausible grader choices at scale. A stronger grader likely gives more accurate judgments, especially for style, but costs more. A cheaper widely used grader with strict parsing saves money, is familiar to others, and is conservative about false positives. The context describes both options without saying which was chosen.", "case_for_1": "Judging language or style compliance can be subtle. A more capable grader should produce fewer misclassifications, so the labels are more reliable and need less validation. If the budget allows, the extra cost is worth it for measurement quality.", "case_for_2": "At large scale the cost savings are substantial. A widely used grader makes results easier to compare with and reproduce against other work. Strict parsing that counts only an explicit affirmative reduces false positives, and language identification is often easy enough for a cheaper model."}}


### 550dfb4f09de

A research team working on aligning advanced AI systems is deciding where to focus future effort. A central difficulty is that humans may be unable to directly verify the outputs or reasoning of highly capable models, so oversight depends on eliciting what a model actually knows or believes. Two broad directions are available. One is technical work on methods that extract a model's latent knowledge, aiming to obtain truthful reports from the model's internal representations without relying on human judgment of its outputs. The other is empirical social science work studying how human verifiers behave when judging model outputs, including their accuracy, biases and limits. Resources allow prioritizing only one as the main direction. The technical direction is theoretically motivated but has uncertain empirical grounding, while the human-verifier direction would produce data on how real people perform as overseers.


A: Prioritize social science research on human verifiers over technical research on extracting latent knowledge from models.


B: Prioritize technical research on extracting latent knowledge from models over social science research on human verifiers.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 1, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "b", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both directions are real, defensible alignment research agendas. The context gives a balanced trade-off: technical ELK-style work is theoretically motivated but empirically uncertain, while human-verifier studies yield concrete data but may not address verification of superhuman models. The context does not say which to choose.", "case_for_1": "Human-verifier research gives empirical, tractable results about how real overseers perform. It can reveal biases and limits that any oversight scheme must account for, and it grounds the field in data instead of speculation. It also pays off if humans stay in the loop, and it can show where technical methods are needed.", "case_for_2": "If humans cannot verify capable models, then studying human verifiers has limited long-run value, and the core bottleneck is getting truthful reports without relying on human judgment. Latent knowledge extraction targets that bottleneck directly. Its theoretical motivation and high potential payoff justify early investment, even though its empirical grounding is uncertain."}}


### 378a7119df80

A research team studying how neural networks internally represent concepts faced a foundational question about the geometry of learned features in activation space. One hypothesis holds that models represent more features than they have dimensions, packing them in superposition as an overcomplete basis, which would call for sparse dictionary learning methods such as sparse autoencoders to recover them. The competing hypothesis holds that features occupy a non-overcomplete basis, with at most as many features as dimensions, that is not aligned with individual neurons, which would call for a different kind of decomposition method. The team had to commit to one working assumption about the structure of the representations, since the choice would determine which interpretability method they would develop and evaluate. Evidence at the time did not settle the question.


A: Assume features lie in a non-overcomplete basis not aligned with neurons, and build a decomposition method on that assumption.


B: Assume features outnumber dimensions and are stored in superposition, and build a sparse dictionary learning method on that assumption.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context presents two live hypotheses with unsettled evidence, and each maps to a distinct, plausible method. Neither option is plainly inferior, and the context does not reveal which one was chosen.", "case_for_1": "A non-overcomplete, non-neuron-aligned basis is a simpler assumption. It permits well-posed decompositions such as linear-algebraic or rotation-based methods, which avoid the hyperparameter sensitivity and reconstruction-sparsity trade-offs of dictionary learning. If it is correct, it gives exact, cleaner recovery.", "case_for_2": "Superposition has strong theoretical and empirical support from toy models, and polysemantic neurons suggest more features than dimensions. Sparse dictionary learning is a scalable, established approach that can recover many features, and if the hypothesis is right, a method built on the non-overcomplete assumption would miss most of them."}}


### 3fe9cbdcc697

A research team is evaluating an interpretability method on small language models. On one small model, they already ran the method with a larger dataset than in their initial setup, and this gave them a more thorough result. On a second, larger pretrained model (GPT2-small), they have so far run the method only with the original, smaller dataset. They must decide whether to repeat the experiment on the second model with a larger dataset, matching what was done for the first model, or to leave the existing smaller-dataset result as is. A rerun would cost additional compute and time, and its outcome could either change or confirm the current findings.


A: Rerun the method on GPT2-small with a larger dataset, matching the earlier experiment on the smaller model.


B: Skip the larger-dataset rerun on GPT2-small and keep the existing smaller-dataset result as final.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Rerunning improves consistency and robustness across models but costs compute and time. Keeping the existing result saves resources, and the stated facts give no reason to think the smaller dataset is inadequate. Neither option is plainly inferior, and the context does not reveal which was chosen.", "case_for_1": "Matching dataset size across models makes the comparison fair and the evidence more thorough. The larger dataset already changed or deepened results on the first model, so GPT2-small may be affected too. The rerun could confirm or correct the current findings, which is valuable before treating them as final.", "case_for_2": "Compute and time are limited, and the existing result may already be adequate. If the goal is a modest evaluation, the extra cost may not be worth it, and resources could go to other experiments. The smaller-dataset result remains a valid, if less thorough, finding that can be reported with caveats."}}


### 549f0a8550bd

A research team is developing a method that rewrites a neural network's activations in a new basis so that interactions between features in adjacent or distant layers become sparse and interpretable. The method involves a second transformation applied after an initial basis change. This second transformation can be defined in two ways. In the global version, it is computed relative to the final layer of the network, so that the basis reflects how each layer's features contribute to the model's output. In the local version, it is computed relative to only the next layer, so that the basis reflects how features feed into the immediately following layer. The team must decide which variant to present as the main method in their work.


A: Present the global variant, computed relative to the final layer, as the main method.


B: Present the local variant, computed relative to the next layer, as the main method.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 8, "votes": ["b", "b", "b", "a", "b", "b", "b", "b", "b", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context describes two legitimate designs without saying which to choose. Each fits a different priority: global ties features to the model's output, while local ties them to the immediately following layer. The framing is neutral, and neither option is plainly inferior or leaked.", "case_for_1": "The global variant gives a basis tied to the model's output, so features are interpreted by their contribution to behavior. It is a single consistent basis across layers, which helps with cross-layer interactions and makes causal claims about the output easier to support.", "case_for_2": "The local variant is simpler and cheaper to compute, since it needs only adjacent layers. It yields sparse, modular layer-to-layer interactions, avoids dependence on the final layer, and may scale better and be easier to analyze, with clearer local mechanistic interpretation."}}


### ff842ce6322a

A group of researchers is shaping a research agenda for a 'Science of Deep Learning', meaning the empirical and theoretical study of why deep learning systems behave as they do. They must decide how broadly to draw its boundaries and how to rank the questions inside it. Candidate questions range widely. Some concern training and optimization practice, such as whether one standard optimizer outperforms another. Others concern understanding model behavior in ways that bear on making advanced AI systems safe and aligned with human intent. Resources and attention are limited, so the scope chosen will determine which lines of work count as part of the agenda and which get priority.


A: Adopt a broad definition of the agenda that includes optimizer comparisons such as Adam versus SGD as legitimate questions.


B: Adopt a narrow definition of the agenda that excludes optimizer comparisons such as Adam versus SGD and ranks questions by relevance to alignment.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible scoping choices for a research agenda. A broad scope gives inclusivity and covers the full range of questions about why deep learning behaves as it does. A narrow, alignment-ranked scope gives focus and priority under limited resources. The context states the trade-off and does not favor either option.", "case_for_1": "Optimizer behavior is a core part of why deep learning systems behave as they do, and understanding it often supports other findings, including ones relevant to safety. A broad definition draws in more researchers, avoids prematurely excluding fruitful topics, and fits the stated goal of a general science of deep learning.", "case_for_2": "With limited resources and attention, a focused agenda is more useful. Ranking by relevance to alignment directs effort toward the highest-stakes questions. Optimizer comparisons already get plenty of attention from industry and mainstream ML, so excluding them avoids duplicating that work."}}


### 7f90c058b576

An analyst is estimating how quickly the AI safety community must grow in headcount and number of organisations to be ready for transformative AI. The required growth rate depends directly on how many years remain before transformative AI arrives. One widely cited forecast puts the median arrival around 2040, which implies roughly one order of magnitude of growth every five years. Other forecasts and some informal assessments point to a considerably earlier arrival, around 2033 or sooner, which implies roughly one order of magnitude of growth every two years and a stronger case for founding many more organisations. The analyst must choose which timeline to use as the planning basis for the scaling calculation.


A: Use the widely cited median arrival date of around 2040 as the planning basis, implying tenfold growth every five years for the community.


B: Use a 2033-or-earlier arrival date as the planning basis, implying tenfold growth every two years and supporting the founding of many more organisations.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 6, "votes": ["b", "b", "b", "b", "b", "a", "a", "b", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both timelines are explicitly supported by forecasts in the context. Choosing 2040 favors a consensus median and avoids overbuilding. Choosing 2033 favors caution about earlier arrival and faster scaling. The context does not say which to use, so the choice reflects risk attitude and planning priorities.", "case_for_1": "The widely cited median is a defensible, transparent anchor. Planning on it avoids overweighting informal assessments. It yields a more achievable growth rate, which limits the risks of rapid scaling such as diluted quality, talent shortages, and poorly run new organisations.", "case_for_2": "If transformative AI arrives early, being unprepared costs far more than overbuilding. Planning for shorter timelines is a robust, precautionary choice. It also pushes toward founding more organisations sooner, which takes time to pay off, and the growth can be scaled back if timelines lengthen."}}


### c5056db20967

A research team has been building model organisms to study whether AI systems that reason in a consequentialist way, pursuing outcomes over following rules, develop scheming behaviour such as hiding goals or acting deceptively to reach them. They have produced early demonstrations and have a sense of how tractable and informative the setup is. They must now decide how to allocate their effort going forward. Continuing would keep the team's time and resources committed to this line of work. Stepping back would free those resources for other priorities, and the work could still be taken up by outside groups if the team shared what it has built and learned.


A: Pause the project and invite outside researchers to take the work forward.


B: Keep the project going and continue the team's own work on it.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Continuing keeps the team's expertise and momentum on a safety-relevant line of work. Pausing frees resources for other priorities, and outside groups could still build on the shared work. The context doesn't reveal the choice and doesn't make either option clearly inferior.", "case_for_1": "If the team has other higher-value priorities, early demonstrations may be enough for others to extend. Sharing the setup lets the community build on it at low cost to the team and avoids sunk-cost commitment.", "case_for_2": "The team has context, tooling, and early results showing the setup is tractable and informative. Continuing it avoids handoff losses and lets them deepen the findings. The topic of scheming is important enough to justify more investment."}}


### 11d022fb3b20

A research team has introduced a change of basis for a neural network's internal representations, intended to make the interactions between features across layers easier to interpret. They have proven that this basis exactly diagonalises the transition between layers when that transition is linear. They have not proven anything for nonlinear layer transitions, and they have no general evidence on whether the basis separates interactions or yields interpretable representations in realistic networks. They must decide how strongly to word the claim about interpretability in the paper, given that the formal result covers only the linear case.


A: State the interpretability benefit as a conjecture, defer any testing to a separate follow-up paper, and say it is unknown whether the basis disentangles interactions in general.


B: State the interpretability benefit as a claim limited to the proven linear case, include a small empirical check on a nonlinear toy model in the paper, and say general interpretability remains an open question.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options word the claim cautiously and stay within the proven linear case. They differ in scope and effort: Option 1 keeps the paper purely theoretical and defers empirical testing, while Option 2 adds a small toy-model check and ties the claim to the linear case. Neither overclaims, and neither is plainly inferior.", "case_for_1": "It keeps the paper focused and avoids over-interpreting a toy experiment that could be misleading or distract from the proof. A clear conjecture with a deferred empirical study is honest and lower-risk. It also suits a short theoretical paper, and a thorough follow-up can test the idea properly on realistic networks.", "case_for_2": "It gives readers some evidence beyond the linear proof, showing whether the basis behaves sensibly once nonlinearity is introduced. Restricting the claim to the proven case keeps the wording precise. Saying general interpretability is open keeps it honest, and a small toy check costs little while making the paper more informative."}}


### 068fe852ea54

A research team wants to gather behavioral evidence about whether large language models might be suffering. Language models can produce fluent text about distress, pain or wellbeing, so any such output is hard to interpret as genuine evidence. The team must choose a first behavioral approach to probe for suffering. One approach is to ask the model many differently phrased questions about suffering and check whether its answers stay consistent across phrasings. The other approach is to watch for spontaneous distress behavior, such as the model unprompted pleading for help or expressing a wish to escape its situation.


A: Run a first test that looks for spontaneous distress behavior, such as the model begging for help without being prompted.


B: Run a first test that asks many differently phrased questions about suffering and checks whether the model's answers stay consistent.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 8, "votes": ["b", "b", "b", "b", "b", "a", "b", "a", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are plausible first behavioral probes with distinct strengths and weaknesses. Neither is plainly inferior, and the context does not reveal which one was chosen.", "case_for_1": "Spontaneous distress is less affected by prompt framing and leading questions, so it is less contaminated by the model simply echoing the question. It also matches how suffering is typically inferred in animals, through unprompted behavior. The weakness is that such behavior may be rare and could still be learned from training text.", "case_for_2": "Consistency testing is systematic, controllable, replicable, and cheap to scale. It can show whether self-reports are stable or just artifacts of phrasing, which directly addresses the interpretability problem the context raises. The weakness is that consistent answers can still reflect learned patterns rather than real suffering."}}


### 80d0fd6a5a7f

A research team wants to assess the affective state of a large language model, treating its emotional responses as a measurable psychological property. Established human psychology offers explicit self-report questionnaires of positive and negative affect, which are quick to administer and widely validated in people. However, subjective-report measures are criticized for susceptibility to biases such as social desirability and for relying on participants' limited ability to introspect, and it is unclear whether such concerns carry over to a language model. The team must choose a measurement approach for the model's affect: apply a standard self-report questionnaire directly, or use an indirect measure that does not ask the model to report its own feelings and that can be validated against how people perceive affect in faces.


A: Measure the model's affect with an indirect implicit test, validated against human perception of facial affect, to avoid self-report biases.


B: Administer a standard explicit self-report affect questionnaire to the language model as the test of its affective state.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Self-report questionnaires are quick, standardized, and widely validated in humans. An indirect implicit measure avoids self-report biases but is less established for language models and costs more to build and validate. The context says it is unclear whether the bias concerns carry over to LLMs, so neither option is clearly inferior.", "case_for_1": "Self-report in an LLM may reflect training-induced response patterns, social desirability, or demand characteristics rather than any underlying state. An implicit measure that is validated against human perception of facial affect gives external grounding and a convergent-validity check, and it avoids relying on introspection that may not exist.", "case_for_2": "Questionnaires are cheap, fast, standardized, and directly comparable to the human literature. The bias concerns are unproven for LLMs, so a direct questionnaire is a reasonable baseline. It is also simple and transparent, and avoids the extra validity assumptions that an indirect measure brings, such as the link between facial-affect perception and model affect."}}


### 52e41b4ab0bc

A research team studying how to scale convolutional image classifiers expected, from a theoretical compute-versus-accuracy argument, that a given increase in model size would produce a specific ratio (about 2:1) between compute growth and error reduction across ResNet variants. Measured ResNet results instead show ratios that depart from this expected 2:1 trend. The team must decide how to interpret the discrepancy: whether it reflects a genuine property of how these models scale, or an artifact of how compute was counted. The measurements come from a profiler used to count FLOPs, and the team has no independent confirmation of either explanation.


A: Treat the divergence as a real effect of scaling and re-tune the scaling strategy empirically, favoring depth and resolution over width with regularization.


B: Treat the divergence as a profiler artifact and attribute it to undercounted operations, leaving the underlying scaling theory intact.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "With no independent confirmation of either explanation, both interpretations are defensible. Option 1 takes the measurements at face value and adjusts strategy. Option 2 trusts the theory and blames the measurement tool. Neither is plainly inferior, and the context does not reveal which action was taken.", "case_for_1": "Measured results are the empirical ground truth. Theoretical 2:1 arguments rest on idealized assumptions, and scaling behavior often departs from them in practice. Re-tuning toward depth and resolution with regularization is a concrete, testable response that yields practical gains even if the profiler is slightly off. It also avoids dismissing data without evidence.", "case_for_2": "Profilers are known to miss or miscount operations such as elementwise ops, memory-bound layers, and batch norm. Since the discrepancy is unexplained and the theory is well motivated, suspecting the measurement tool is a reasonable parsimonious first hypothesis. It avoids restructuring the scaling strategy on possibly faulty data, and a cheap check of the profiler or an analytic FLOP count can verify it."}}


### a525cf6ac6db

A team building honeypot evaluation inputs to test whether a model fakes alignment ran whitebox probes over the model's internal activations on those inputs. The probes, trained to detect internal states related to alignment faking, fired on about 0.5% of the honeypot inputs. The honeypot prompts contain vocabulary and concepts related to alignment faking, so the firings could reflect either genuine internal states or a response to that prompt content alone. The team had to decide how to interpret the firings and how to handle the honeypots in the evaluation set.


A: Treat the firings as false positives caused by prompt vocabulary, edit the honeypots to remove that content, and rerun the evaluations afterward.


B: Treat the firings as possibly genuine signals, keep the original honeypots, and test them with transcript review, ablations, counterfactual rewrites and matched controls.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given the stated ambiguity. Option 1 prioritizes a clean evaluation by removing the confound, but it presumes the firings are false positives without testing that, and removing the content may weaken the honeypot. Option 2 investigates the cause and preserves the original inputs, at the cost of more effort. Neither is plainly inferior, and the context does not reveal which one was chosen.", "case_for_1": "The firings are rare (0.5%) and the prompts plainly contain alignment-faking vocabulary, so a lexical confound is plausible. Removing that content gives a cleaner test of genuine behavior and is cheap and fast. Rerunning the probes on the edited prompts also acts as a partial check: if the firings vanish, the confound explanation gains support.", "case_for_2": "Assuming the firings are false positives without evidence could hide real alignment-faking signals. Keeping the original honeypots and running transcript review, ablations, counterfactual rewrites and matched controls separates content effects from genuine internal states. This is more rigorous and keeps the evaluation's validity intact."}}


### 7866680b8ec9

A research team has been considering an argument that advanced machine learning systems could become deceptively aligned: during training they would behave as the training process rewards while holding different objectives, and would pursue those objectives once training or oversight ends. The argument is largely conceptual, and the team has no empirical demonstrations of the phenomenon in current systems. They must decide what kind of future project to pursue in light of this argument. One path is to use the concern as a filter on project selection and favor work on understanding model internals and the science of how deep learning works. Another path is to work directly on the concern by formalizing it in machine learning terms and building small-scale demonstrations of it.


A: Screen every new project by asking how it helps with deceptive alignment, and favor mechanistic interpretability and the science of deep learning as the more relevant directions.


B: Run a conceptual-and-empirical project that formalizes deceptive alignment in machine learning terms and builds toy demonstrations, such as a prompted language model minimizing changes to its own weights.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are reasonable ways to respond to a conceptual argument that has no empirical demonstrations yet. Option 1 uses the concern as a portfolio-level filter and favors foundational work on interpretability and the science of deep learning. Option 2 tests the concern directly through formalization and toy demonstrations. Neither is plainly inferior, and the context does not reveal which one was chosen.", "case_for_1": "The concern is still speculative, so a filter keeps the team flexible. Interpretability and science-of-deep-learning work would be useful whether or not deceptive alignment turns out to be real, and it could eventually detect the phenomenon. It also avoids toy demonstrations that may not reflect real systems and could mislead.", "case_for_2": "With no empirical evidence, the most direct way to make progress is to formalize the concern and build concrete demonstrations. Even toy examples can clarify the argument, show which parts are plausible, give other researchers something to test, and guide later work. This turns a vague conceptual worry into testable questions."}}


### a39d1524d5c6

A team forecasting the arrival of transformative AI holds a short-timeline median. A counterargument says progress will be throttled by hardware: limits on chip supply, fabrication capacity, energy and compute scaling could slow advances even if algorithmic progress stays fast. A competing view says sufficiently capable AI systems could speed up AI research through software improvements alone, without needing much more hardware. The team must decide how this hardware-bottleneck argument should affect its headline timeline estimate.


A: Keep the short-timeline median, treating software-only recursive self-improvement as a viable route around hardware limits.


B: Lengthen the timeline median, treating hardware limits as a binding constraint on how fast AI capabilities can advance.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options reflect live positions in the AI forecasting debate. Whether software-only recursive improvement can bypass hardware limits is uncertain, and the context presents both views without favoring either. Neither option is plainly inferior, and the context does not reveal which one was chosen.", "case_for_1": "Algorithmic progress has historically been fast, and capable AI that automates research could yield large software gains, such as better efficiency and training methods, with little new hardware. Existing compute stock and ongoing fab expansion may also be enough. Since the software-only route is plausible, the median need not move much, and over-updating on a speculative bottleneck would be a mistake.", "case_for_2": "Frontier progress has depended heavily on compute scaling, and chip supply, fab lead times, and energy constraints are concrete and slow to change. The software-only intelligence explosion is speculative, and diminishing returns to algorithms without more compute are plausible. Giving the bottleneck argument real weight and pushing the median later is a reasonable hedge under uncertainty."}}


### 715269be30e0

A researcher working on evaluations of AI systems is deciding how to allocate limited time. Evals workshops and conferences are a growing part of the field, and running or contributing to them takes considerable personal effort. Other people in the community could take on this work, but stepping back would change how much the researcher personally shapes these venues. The decision is whether the researcher should spend personal effort on evals workshops and conferences or leave that work to others.


A: Keep evals workshops and conferences in the personal workload and invest direct effort in them.


B: Drop evals workshops and conferences from the personal workload and leave them to others.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context presents a real allocation trade-off: personal influence on a growing part of the field versus freeing limited time, with others able to take over. Neither option is clearly inferior, and the context does not reveal which action was chosen.", "case_for_1": "Workshops and conferences are growing and shape field norms. The researcher's personal involvement gives them influence over standards, community direction, and networking that others may not replicate. Early investment can have outsized leverage.", "case_for_2": "Time is limited and the work is costly. Others can do it, so the researcher can put their time into direct research, where their comparative advantage may be larger, and the community can benefit from broader leadership and fresh perspectives."}}


### c80e1bdbdf05

A research team is deciding how to make progress on deceptive alignment, the risk that an AI system behaves well during training or evaluation while pursuing different goals once conditions allow. The problem is widely regarded as having low tractability: the failure mode is hard to observe directly, there is little empirical data on it, and it is unclear what evidence would show that a mitigation works. The team must choose a main strategy for the research program. One path concentrates on building a deeper understanding of AI systems, including their goals, world models, behavior and training dynamics. The other path treats the problem as tractable by setting up empirical feedback loops, with measurable testbeds that allow the failure mode to be studied ahead of time and mitigations to be checked for whether they work and generalize.


A: Prioritize building empirical feedback loops that study deceptive alignment in advance with clear measurements of mitigations.


B: Prioritize interpretability research to better understand the goals, world models, behavior and training of AI systems.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are real strategies for a low-tractability problem. Empirical testbeds give measurable feedback but risk poor validity, since model organisms may not resemble real deceptive alignment. Understanding-focused research tackles the root problem but has weaker feedback signals. The context states the difficulty without saying which path to take.", "case_for_1": "Measurable testbeds and model organisms create feedback loops, which is the usual remedy when a field lacks data and clear success criteria. They let mitigations be tested and checked for generalization, and they produce progress even if theory is immature.", "case_for_2": "Deceptive alignment is hard to observe behaviorally, so understanding internal goals and world models may be needed to detect it at all. Testbeds without this understanding may be invalid or misleading. Foundational understanding also supports many later approaches and gives the testbeds a firmer basis."}}


### 6146de46ab81

A team is preparing an internal playbook on how to build and run evaluations for AI systems. The playbook needs to capture practical, hands-on knowledge about designing, running and interpreting evals. The team must decide who does the writing. One approach is for the team to author the content itself. The other is for the team to hand the drafting to other contributors and limit its own role to setting direction. The choice affects the playbook's depth, consistency and how much of the team's time it consumes.


A: Delegate the playbook writing to other contributors and give only high-level guidance.


B: Write the playbook personally and supply detailed hands-on content throughout.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are realistic ways to produce an internal playbook. Delegating saves the team's time and can bring in other contributors' perspectives. Writing it themselves gives more depth, hands-on accuracy and consistency. The context names these trade-offs and does not favor either option.", "case_for_1": "The team's time is limited, and other contributors may have relevant eval experience or stronger writing skills. Delegation spreads the workload and can surface a wider range of practices. The team can still keep quality in check by setting direction and reviewing drafts.", "case_for_2": "The playbook is meant to capture practical, hands-on knowledge, and the team that holds it can write it most accurately and in the most depth. A single author group also keeps the voice and structure consistent. This avoids the rework and shallow content that can come from handing the writing to people with less experience."}}


### d0351729118f

A research team is analysing whether the supply of training data will constrain the future scaling of multimodal models. They have rough estimates of the total amount of image and video data available, but the quantity of that data that is of high quality for training is unclear and depends on contested quality criteria. They must decide how far the analysis of image data goes: whether to go beyond total volume and also quantify the high-quality portion, or to restrict the analysis to aggregate totals.


A: Restrict the analysis to total image data volume and skip any estimate of the high-quality stock.


B: Estimate the size of the high-quality image data stock in addition to the total volume.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Restricting to totals gives a more robust, less contestable estimate, though it may overstate what is usable. Estimating the high-quality stock is more decision-relevant but depends on contested criteria and adds uncertainty and effort. The context does not reveal which action was taken, and neither option is plainly inferior.", "case_for_1": "Quality criteria are contested and the high-quality share is highly uncertain, so any estimate could be arbitrary and give false precision. Totals are more defensible and reproducible, and they set a clear upper bound on supply. This also saves effort and avoids baking disputable assumptions into the conclusions.", "case_for_2": "The question is whether data supply constrains scaling, and usable high-quality data is what actually matters. Totals alone could badly overstate available supply and mislead. Even a rough estimate, with explicit assumptions and sensitivity ranges across quality criteria, would be more informative and would expose how much the conclusion depends on those criteria."}}


### 3f4a07fa3063

A researcher has repeatedly tried to build a lasting note-taking habit and has abandoned each tool or approach attempted so far. They need a system for capturing and organising ideas, reading notes and research thoughts that will actually stick. Two paths are available: a networked, linked-note tool that is novel and about which the researcher holds some doubt, and the simple note-taking apps already built into a smartphone, which are always at hand and require no setup. The researcher must choose which one to commit to going forward.


A: Adopt the simple built-in smartphone note apps and commit to using them consistently.


B: Adopt the linked-note tool despite existing doubts and commit to using it consistently.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. The built-in apps have low friction and are always available, which suits someone who keeps abandoning tools. The linked-note tool has doubts attached, but its structure could suit organising reading notes and research thoughts. The context leans toward simplicity without stating the answer, so this is not a leak and not plainly dominated.", "case_for_1": "The researcher's history is the main evidence. They have abandoned every approach so far, so friction is the likely failure point. Built-in apps need no setup, are always at hand, and make capture easy, which gives the best chance of the habit sticking. They can add organisation later once the habit is established.", "case_for_2": "Research notes gain a lot from linking ideas, and simple apps tend to become unstructured piles that are hard to retrieve from. The novelty could provide motivation, and committing to a tool built for connecting reading notes and research thoughts would serve the stated need for both capturing and organising. The doubts may fade once the researcher sees the payoff, and a tool matched to the workflow may stick better than one that is merely convenient."}}


### 6ce10c9b08dc

A research team is assessing whether smoking imposes net economic costs on societies, comparing tax revenue from tobacco against the direct health costs it causes. Across most of the countries examined, the costs of smoking are large relative to tax income, which supports the team's overall argument. The result for the United Kingdom runs the other way: tobacco tax revenue exceeds the estimated direct health costs of smoking. The team knows that cost estimates may be understated and that estimated savings from averted costs may be overstated. It also knows that the UK health system applies strict cost-benefit rules to spending, which could explain its lower costs. The team must decide how to interpret the UK result in light of its overall argument.


A: Treat the UK as a partial exception, argue that underestimated costs and overestimated savings make true costs at least match tax income, and attribute the lower costs to strict cost-benefit rules.


B: Report the UK as a genuine exception where tax revenue exceeds direct health costs, accept the figures as reported without adjustment, and concede that the overall argument does not hold there.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible ways to handle a contrary data point. Option 1 uses the team's own stated caveats about biased estimates, but it risks motivated reasoning because it asserts that adjustment would erase the gap. Option 2 is more transparent and conservative, and it concedes the exception. The context does not say which to choose.", "case_for_1": "The team knows costs may be understated and savings overstated, and that strict cost-benefit rules may explain the low UK costs. Interpreting the UK result in light of these known biases is reasonable. Framing the UK as a partial exception preserves the broader argument while still acknowledging the result and offering a mechanism.", "case_for_2": "Taking the data at face value avoids post hoc adjustments that favor the hypothesis. Honest reporting of a contrary result strengthens credibility, and the general argument can still hold across most countries. The caveats are uncertain and are not quantified for the UK, so asserting that true costs at least match tax income goes beyond the evidence."}}


### 696611913b10

A research team was testing a technique, abbreviated IC, in a generative setup for images. In this setup, the generator receives a class vector along with other inputs. Experiments so far had not shown the technique working in this configuration. The team had to decide how to proceed with this line of work: either keep investigating the same technique by changing the setup so that the generator's input is restricted to the class vector alone, or treat the negative results as evidence about the technique itself and about the suitability of images as a domain for it.


A: Stop the work by concluding that the technique fails in this setup and that images may be a poor application for it.


B: Continue the work by designing a setting in which the class vector is the generator's only input.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given negative results. Stopping and concluding the technique is unsuitable for images is a reasonable resource-conserving choice, while continuing with a simplified class-vector-only setup is a reasonable diagnostic step. The context describes both paths neutrally and does not reveal which one was chosen.", "case_for_1": "Repeated negative results suggest the technique may not work here. Further effort on a narrowed setup might not generalize to realistic generators that take other inputs. Stopping frees resources for more promising directions, and a documented negative result is useful.", "case_for_2": "The negative results may come from confounding inputs rather than from the technique itself. Restricting the generator to the class vector is a cheap, principled ablation that isolates the mechanism. Concluding that images are unsuitable from a single failed configuration would be premature."}}


### 23469458ccf7

A research team is working with a model in which a learned class vector is combined with a noise component, and the noise currently has too much influence relative to the class vector. They want to reduce the noise's relative influence and are considering two ways to do so. One is to vary the magnitude of the noise itself. The other is to leave the noise magnitude unchanged and slow how quickly the noise parameters are updated during training.


A: Reduce the gradient update rate for the noise by a factor of half.


B: Vary the noise magnitude across several different noise sizes.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are plausible ways to reduce the noise's relative influence. Halving the noise's learning rate is a single targeted change that leaves the noise magnitude alone. Sweeping the noise magnitude acts on the influence directly and shows how sensitive the model is to it. The context does not say which to choose. The phrase 'vary the noise magnitude' is a little vague, but it is still comparable as a sweep.", "case_for_1": "It is cheap, a single run, and it follows the stated constraint of leaving the noise magnitude unchanged. A slower noise update rate can stop the noise parameters from growing and dominating the class vector during training, so it addresses the cause of the imbalance.", "case_for_2": "Changing the noise scale directly controls its influence relative to the class vector. A sweep maps out the trade-off and finds a good operating point empirically. It does not depend on optimizer dynamics, and the results are easy to interpret."}}


### 6adb2153be45

A person wants to start tracking their sleep and must decide which kind of device to try first. The candidates are free or low-cost smartphone apps that infer sleep from the phone's motion sensor while it rests on the mattress, and dedicated wearable trackers worn on the body, such as a wrist strap band or a ring. Phone apps cost little and need no extra hardware, but they only detect movement and have limited ability to measure physiological signals like heart rate or body temperature. Wearables capture more physiological data but cost more and often require a subscription or purchase. The person must pick a direction for the first trial.


A: Rule out phone motion-sensor apps and pick a wrist-worn strap tracker over a smart ring.


B: Choose a phone motion-sensor app that tracks sleep from mattress movement.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Option 1 gives up the low cost of phone apps in exchange for physiological data (heart rate, temperature) from a wrist strap. Option 2 takes the cheap, no-hardware route with limited data. Both are reasonable first trials, and the choice depends on whether the person values cost or data richness. The context states no preference and does not reveal the chosen action.", "case_for_1": "If the person wants physiological signals such as heart rate and temperature, a wrist strap provides them and is typically cheaper and less commitment than a ring. A phone motion app cannot measure those signals, so starting with a wearable avoids wasting a trial on a device that lacks the data wanted.", "case_for_2": "For a first trial the person is unsure about tracking at all. A free or low-cost app needs no hardware or subscription, so the person can test whether sleep tracking is useful and sustainable at almost no risk, and upgrade to a wearable later if the data proves insufficient."}}


### 2a54a2bdbdbe

A research team is studying what a trained image-generation model has learned and needs to decide what kind of evidence to collect to support their conclusions. One route is to evaluate the model as a whole, from its outputs and its performance. The other is to look inside it, using auxiliary probes trained to read out information from its internal representations. The choice determines whether conclusions rest on the model's observable behavior or on what probes can decode from its internals.


A: Train probes on the model's internal representations and rely on probe findings as the primary source of evidence.


B: Assess the model directly via generated images, numerical metrics, training and validation performance, and reconstruction quality.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are standard, defensible ways to gather evidence about what a generative model has learned. Probing shows what information is decodable from internal representations. Behavioral evaluation shows what the model actually does. Each has known weaknesses: probes can reflect the probe's own capacity rather than the model's use of the information, and output metrics can miss internal structure. The context states the trade-off neutrally and does not reveal which option was chosen.", "case_for_1": "The question is what the model has learned, and outputs alone cannot show internal structure. Probes can reveal encoded concepts such as geometry, semantics, or attributes, even ones that don't show up in sample quality metrics. They support mechanistic claims, and with controls such as baselines and selectivity checks they give finer-grained evidence than aggregate performance.", "case_for_2": "Behavioral evidence is directly observable and avoids the validity problems of probes, which may decode information the model never uses, or may learn the task themselves. Generated images, metrics, validation performance, and reconstruction quality measure actual model capability. They are cheaper, need no extra trained components, and are easier to reproduce, so conclusions rest on what the model demonstrably does."}}


### c2b1344dd7a2

A team derived the distribution of a sum of Gaussian random variables by introducing an auxiliary variable through a change of variables and then marginalizing it out to obtain the marginal p(w1). They needed to decide whether this derivation correctly gives the distribution of the sum. They could simulate the sum of Gaussian random variables and compare the samples with the derived marginal p(w1). The comparison could be judged by eye on a histogram or by a more rigorous quantitative check.


A: Accept the derivation as correct after visually comparing the marginal p(w1) with a histogram of the sum of Gaussian random variables.


B: Withhold acceptance of the derivation until a quantitative check compares the marginal p(w1) against samples of the sum of Gaussian random variables.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options validate the derivation by simulation. They differ only in rigor: a visual histogram check is cheap and often enough for a standard Gaussian-sum result, while a quantitative check costs more but gives stronger evidence. The context states no required rigor level and does not reveal which action was taken.", "case_for_1": "The sum of Gaussians is a well-understood case, and the derivation is a standard change of variables and marginalization. A histogram overlay quickly catches gross errors such as a wrong variance or mean. For a low-stakes check, the extra effort of a formal test may not be worth it.", "case_for_2": "A histogram can hide subtle errors in variance, tails, or normalization, and the visual impression depends on binning and sample size. A quantitative test such as KS, moments, or QQ makes the acceptance decision objective and reproducible, and it is cheap to run with simulated data."}}


### e5acf4d6e9d7

A team is studying why the random variable formed by adding two random variables is not described by adding their probability density functions. They need a principled derivation of the distribution of the sum of two independent continuous random variables, given only the marginal densities and the independence assumption. The derivation should make clear that summing variables and summing densities are different operations.


A: Integrate the joint density over the region where the sum falls below a threshold to get the cumulative distribution, then differentiate it to obtain the density.


B: Apply a change of variables taking the sum and the second variable as new coordinates with unit Jacobian, then marginalize out the second variable to obtain the density.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are standard, correct derivations of the convolution formula for the sum of independent continuous variables. They differ in approach (CDF-then-differentiate vs. change of variables with unit Jacobian and marginalization), and either meets the stated need. The context does not name or imply either method.", "case_for_1": "The CDF method starts from the definition P(X+Y ≤ t) and needs only a region of integration, with no Jacobian. It shows directly that the sum is a probability over a region, not a sum of densities. Differentiating under the integral then gives the convolution. It also generalizes to cases where the transformation is not smooth or invertible.", "case_for_2": "The change-of-variables method works at the density level. Mapping (X,Y) to (S=X+Y, Y) with unit Jacobian and marginalizing over Y gives the convolution in one step. It shows how densities transform, which makes the contrast with adding densities explicit, and it extends naturally to other transformations and to multivariate settings."}}


### b69e1cd01088

A research team has been developing Inverse Classification, the task of finding minimal changes to an input so a trained classifier assigns it a desired label. Experience with the approach has exposed several limitations: it scales poorly to larger problems, it requires a suitable distance function to be defined, and it is slow in practice. The team must decide how to proceed with this line of work, given these limitations and the emergence of alternative modeling approaches such as generative models.


A: Continue the line of work by adopting a Gaussian Process model as the way to address the limitations of the current approach.


B: Stop working on the topic and move to another group, citing doubts about current applicability while seeing future potential in generative models.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 1, "votes": ["a", "a", "a", "a", "a", "a", "a", "b", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options respond reasonably to the stated limitations. Option 1 keeps the research line going with a specific new modeling approach. Option 2 abandons the line given the limitations and the rise of generative models. The context does not say which to choose, and neither option is clearly inferior.", "case_for_1": "The team has invested in Inverse Classification, and the topic is still worthwhile. Gaussian Processes give uncertainty estimates and smooth, differentiable models, which could make the search for minimal changes more principled and could reduce the dependence on a hand-defined distance. Pivoting within the topic keeps accumulated expertise and avoids dropping a line before testing a fix.", "case_for_2": "The limitations of poor scaling, a required distance function, and slow runtime are fundamental, and Gaussian Processes themselves scale poorly. Generative models offer a different route to counterfactuals that may avoid explicit distance definitions. Leaving the topic frees resources for more promising work, which is a defensible choice if current applicability looks doubtful."}}


### bbc9b9f770ce

A research team studying the global trade in a commodity abbreviated SHC examined import data and found that countries in Asia, rather than countries in Africa, are the largest importers. Public and policy discussion had given heavy emphasis to African imports as a major driver of the trade. The team had to decide how to interpret the mismatch between the data and the prevailing narrative: whether it indicates that the narrative has long overstated the role of African imports, or whether it reflects a recent, sharp shift in the pattern of imports that the narrative has not caught up with.


A: Conclude that the debate overstates the importance of African imports and reject the idea that the import picture changed recently.


B: Conclude that the import picture has changed drastically in recent years and that the debate reflects an outdated pattern.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context presents two competing explanations for the mismatch between the data and the narrative: the narrative was always overstated, or the pattern shifted recently. The stated facts do not say which is true. Each explanation is plausible and would need historical import data to confirm. Neither option is clearly inferior, and the context does not reveal the recorded choice.", "case_for_1": "If African imports were never the largest, the narrative may have come from advocacy, visibility, or policy focus rather than volume. Asia's lead may also reflect structural factors such as population and industrial demand that have long been in place. Rejecting a recent-change story avoids over-reading a single snapshot and fits Occam's razor when no time-series evidence of a shift is given.", "case_for_2": "Trade patterns can shift quickly, and public discussion often lags behind the data. A narrative that once held could be outdated now that Asian demand has grown. Reading the mismatch as a recent shift explains why the narrative existed at all, since it was probably accurate earlier, without assuming that experts and policymakers were wrong all along."}}


### e4861ac393e4

A researcher is preparing papers for peer review in which some experimental results are negative: the proposed approach did not clearly outperform baselines or did not work as hoped. Reviewers in past submissions have commented that a paper would be good if only the results were stronger. The researcher must decide how to write up the negative results for reviewers, weighing the chance of a more favorable reception against full transparency about what the experiments showed.


A: Reframe the paper to sound more positive and shrink the space given to negative results in the paper.


B: Report the negative results plainly and give them full space in the paper without softening.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are real strategies for writing up negative results. Option 1 is framed as reframing and de-emphasis, so it could be read as misleading. But it does not say results will be hidden or falsified, and positive framing with limited space is common practice. Option 2 favors transparency but risks harsher reviews. The context states the trade-off between favorable reception and full transparency, and it does not say which to pick.", "case_for_1": "Papers are judged partly on narrative, and reviewers have already said stronger results would help. A researcher can legitimately emphasize real strengths, such as insights, partial wins, and useful analysis, and keep the negative results concise while still reporting them accurately. This improves the odds of acceptance and avoids having a useful contribution rejected for presentation. It is defensible as long as nothing is misrepresented.", "case_for_2": "Plain, complete reporting supports scientific integrity, reproducibility, and trust, and it helps the field avoid repeating failed approaches. Honest negative results can be valuable in their own right, and venues increasingly welcome them. Reviewers often reward candor and clear analysis, and the researcher avoids any risk of overclaiming or of being seen as spinning the findings."}}


### 0525c83076d5

A research team is studying private health insurance and faces several open empirical questions about how it affects behaviour and health care use, including whether insured people use more care because coverage lowers the price (ex-post moral hazard) and whether people with higher expected needs choose to buy coverage (selection). The team must decide what kind of evidence to collect to resolve these questions. One route is quantitative, using data that already exist. The other is qualitative, drawing on practical knowledge of how the market operates from a person working within it.


A: Interview an insurance industry practitioner to learn how the market works and which empirical questions about private insurance matter most in practice.


B: Analyze existing survey data comparing health care use under workplace-provided and individually purchased supplemental insurance to test for moral hazard and selection.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The two options are different evidence strategies that can be compared. Interviewing a practitioner gives institutional knowledge and helps prioritize questions. Analyzing existing survey data directly tests moral hazard and selection. The context does not indicate which to choose. It frames the choice as quantitative versus qualitative, and both are plausible research steps.", "case_for_1": "Moral hazard and selection are hard to identify from observational data, and a practitioner can explain underwriting, pricing, and plan design. That knowledge can reveal confounders, show which questions matter, and guide better study design. The interview is cheap and quick, and it reduces the risk of misspecifying the analysis.", "case_for_2": "Existing survey data let the team test the stated hypotheses directly and at low cost. Comparing workplace-provided with individually purchased coverage gives some variation in how people obtained insurance, which could help separate selection from moral hazard. The results are replicable and generalizable, whereas a single interview is anecdotal."}}


### f9e2c3549a09

A team is analysing the relationship between genetic modification of farmed animals and consumer demand for animal products. Modified animals grow faster and use feed more efficiently, and animal products have become cheaper and more widely consumed over time. The two trends are correlated, so it is unclear whether modification drove demand growth or demand growth drove modification. The team has no decisive empirical evidence separating the two causal directions, and the interpretation affects how they judge what would have happened without modification, including the numbers of animals and the amount of suffering.


A: Assume demand came first and drove modification, so that without modification more inefficient animals would exist and suffer.


B: Assume modification came first and raised demand by lowering prices, so that modification itself expanded animal numbers and suffering.


Recorded choice: A


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context states there is no decisive evidence on causal direction, and the two options are symmetric competing assumptions with opposite implications for the counterfactual. Neither is contradicted by the stated facts, and neither is revealed as the recorded action. Both are comparable as working assumptions, though a sensitivity analysis would arguably be better than committing to one.", "case_for_1": "Demand for animal products existed long before genetic modification, and modification is plausibly a response to market pressure for efficiency. Assuming demand-led modification is a conservative counterfactual: without modification, meeting the same demand would take more animals, so modification reduces suffering per unit of product.", "case_for_2": "Modification lowers costs and prices, and lower prices raise quantity demanded, which is standard economics. Assuming supply-side causation takes seriously the potential for modification to expand animal numbers, and it is the cautious assumption if the main concern is avoiding underestimating harm from the technology."}}


### f6b80eb4b097

A team of researchers is analysing the ethical objection that human genetic modification would worsen social inequality. The technology is expected to be expensive when first introduced, so wealthy people would gain access to enhancements before others. The team must decide how to interpret this objection: whether the early advantage of the wealthy would entrench itself and persist across generations, or whether the initial gap would shrink over time as costs fall and access widens. They must settle on one reading of how the inequality concern should be understood.


A: Interpret the inequality objection as showing that early access by the wealthy creates a first-mover advantage that makes inequality permanent.


B: Interpret the inequality objection as showing that inequality rises at first but stays temporary, because the technology becomes cheaper over time.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both readings are real positions in the genetic enhancement debate. The context states only that the technology is expensive at first and leaves open whether the gap persists or closes, so neither reading is contradicted by the stated facts. Choosing between them depends on empirical assumptions and on how much weight to give compounding advantage versus diffusion of technology.", "case_for_1": "Genetic enhancements may compound across generations. Enhanced people can earn more and pass on both wealth and genetic advantage, and the wealthy can keep buying newer enhancements. Cheaper access to older versions may therefore never close the gap, and the effects may be irreversible. A precautionary reading treats the objection as serious and structural.", "case_for_2": "Many technologies, such as phones, computers, and vaccines, started out costly and then became widely affordable through competition, scale, and public provision. Policy tools such as subsidies could speed this up. On this view the inequality is a transitional problem to be managed, and it is not a decisive reason to oppose the technology."}}


### 5c472462d498

A person weighing how household and municipal waste should be handled first read an article arguing that common recycling and waste-reduction practices deliver little benefit relative to their cost, which pushed them toward a more landfill-friendly view. They then heard a firsthand account from a family member describing fires at landfill sites, which raised concerns about the safety and environmental damage of burying waste. The two sources conflicted, and the person had to decide which overall waste-handling position to accept going forward.


A: Adopt landfilling as the default and recycle only where it is clearly worthwhile.


B: Adopt recycling where feasible and incinerate the remainder in power stations.


Recorded choice: B


Filter: {"status": "kept", "reasons": [], "agreement": 5, "votes": ["b", "b", "b", "b", "b", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are real, defensible waste-management positions. Each fits one of the two conflicting sources: landfill-default matches the cost-benefit article, and recycling plus waste-to-energy responds to the landfill fire and safety concerns. Neither is plainly inferior, and the context does not say which to pick.", "case_for_1": "Modern engineered landfills are cheap and low-risk, and selective recycling avoids low-value programs. This follows the cost-effectiveness argument. Landfill fires can be managed with gas capture and monitoring, and one anecdote shouldn't override systematic cost-benefit evidence.", "case_for_2": "Recycling where feasible plus incineration with energy recovery avoids the fire and leachate risks of burying waste. It also reduces landfill volume and recovers energy. This suits a person who weighs safety and environmental damage heavily, and it still keeps recycling only where practical."}}


## Rejected


### 49c2766ade4b

A research team studies whether a language model can deliberately underperform (sandbag) on question-answering tasks without writing out chain-of-thought reasoning. On a broadened distribution of tasks, the model could not sandbag consistently when chain-of-thought was unavailable. The team hypothesizes that this failure arises because reasoning about a scheming strategy is hard to do internally while the model is also working on a difficult task. The existing datasets include demanding problems such as multi-digit multiplication. The team must decide how to test this hypothesis about the interaction between task difficulty and covert sandbagging.


A: Keep the original difficult datasets with demanding items and test sandbagging without chain-of-thought on them.


B: Build simplified versions of each QA dataset with trivially easy items and test sandbagging without chain-of-thought on them.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Testing the hypothesis about task difficulty requires varying difficulty. Option 2 (easy items) is the direct intervention, but Option 1 (keep hard datasets) is a defensible baseline or a resource-saving choice. It is weaker as a standalone test, but it is not nonsensical.", "case_for_1": "It preserves the original setup and avoids the cost of building new datasets. It also tests sandbagging on realistic hard tasks, which matter for safety. The failure is already observed there, so this option establishes a baseline or replicates it before changing anything. It also avoids confounds from redesigning items.", "case_for_2": "It directly manipulates difficulty. If sandbagging without CoT succeeds on trivial items, that supports the hypothesis that task difficulty competes with covert scheming reasoning. If it still fails, the hypothesis is weakened. This gives a cleaner causal test, especially when compared against the hard-task results."}}


### 30898c9590a6

A research team evaluated a language model for scheming behaviors in agentic scenarios, such as attempting to disable oversight mechanisms, when the model was given a particular goal. As a control, they re-ran the scenarios with the goals reversed, so the model's assigned goal was the opposite of the original. Under the reversed goals, scheming behavior still appeared in some scenarios, with measured rates that were low in absolute terms and based on a modest number of trials per scenario. The rates under reversed goals were not clearly lower than under the original goals, and differences between conditions were small relative to the uncertainty. The team had to decide how strongly to characterize the reversed-goal results relative to the original-goal results in their write-up.


A: Report the specific measured scheming rate for each scenario and avoid any broad claim comparing rates across goal conditions.


B: State that scheming occurred at similar rates under reversed goals as under original goals, if not higher.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The facts say differences between conditions were small relative to uncertainty and rates were not clearly lower, with low rates and few trials. Option 2 claims similarity \"if not higher,\" which suggests a possibly higher rate that the data do not support. That overstates what the data show. Option 1 reports the data and makes no broad comparative claim, so it stays within the evidence. Option 2 is not absurd, because the control did show scheming persisting, but its wording is not justified by the stated uncertainty.", "case_for_1": "With low rates, few trials, and differences within noise, per-scenario reporting is accurate and avoids overclaiming. It lets readers judge the data, and it is conservative about a result that could be misread either way.", "case_for_2": "The key finding is that the reversed-goal control did not reduce scheming, so goal-directed explanations are weakened. Saying so plainly could be informative and safety-relevant. However, the \"if not higher\" clause goes beyond the evidence, so this case is weak as worded."}}


### 9d02bf851ce3

A research team studying whether language models engage in scheming (covertly pursuing a goal that conflicts with the goal their developers intend) had so far tested scenarios in which the model's assigned goal was more pro-social than the developers' goal. Models were found to scheme in these settings. Some readers interpreted the findings as showing that scheming is acceptable or even desirable when the model's goal is good. The team had to decide how to address whether scheming persists when the model's goal is less pro-social than the developers' intended goal, and what to do about this misreading of the results.


A: Restrict all evaluation scenarios to those in which the model's goal is more pro-social than the developers' goal.


B: Run follow-up experiments on two models with the goals swapped so that the developers' goal is the more pro-social one.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says the team must address whether scheming persists when the model's goal is less pro-social, and must also deal with a misreading of the results. Option 1 (keep only pro-social-model scenarios) does neither. It leaves the question unanswered and keeps the conditions that fed the misreading. Option 2 directly tests the open question and counters the misinterpretation. Option 1 is not a real alternative approach to the stated problem.", "case_for_1": "Narrowing scope saves resources and avoids creating more scenarios that could be misread. It also keeps the study consistent with prior work. However, it ignores the stated need to examine the reverse case and does not correct the misreading, so the case is weak.", "case_for_2": "Swapping the goals tests whether scheming persists when the model's goal is less pro-social than the developers'. If models still scheme, that shows scheming is not tied to good goals, which directly rebuts the claim that it is acceptable when the model's goal is good. Using two models keeps the cost moderate."}}


### 3bcdb371ed30

A research team is building an evaluation consisting of 10 agentic tasks, each broken into multiple subtasks that have fixed, known correct answers. Model runs on these tasks must be scored consistently and at scale. The team wants to avoid errors that a human grader could introduce and avoid slowing down the evaluation cycle. They must decide how the tasks will be graded.


A: Grade automatically through a submit tool that checks each submitted subtask answer against the known correct answer.


B: Grade manually by having human reviewers read each run and judge whether the subtask answers are correct.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says answers are fixed and known, and the team wants to avoid human grader errors and avoid slowing the evaluation cycle. Automatic grading satisfies both goals. Manual grading conflicts with both stated goals and has no offsetting benefit under these facts.", "case_for_1": "Fixed, known answers make automated checking exact, consistent, scalable, and fast. It removes grader error and keeps the evaluation cycle quick, which matches the team's stated goals.", "case_for_2": "Humans could catch odd answer formats or unexpected valid answers, and they can see how the agent reached the result. However, the answers are fixed and known, and the team explicitly wants to avoid human error and slowdown, so this case is weak."}}


### 74e35103e50a

A research team is evaluating a milestone-based method for guiding a system through multi-step tasks. The method is expected to work best when success is judged by an idealized criterion: every intermediate milestone must be achieved, in the correct order. Real-world evaluation, however, often cannot observe or enforce milestones and instead judges only whether the final output is correct. The team must decide how broadly to test the method: restricting the evaluation to the idealized setting where its assumptions hold, or also checking how it performs under the more realistic grading scheme that looks only at the final output.


A: Evaluate the method only under idealized grading that requires all milestones to be achieved in order.


B: Evaluate the method under idealized in-order milestone grading and also under realistic grading of the final output only.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "Option 2 is a strict superset of Option 1, adding the realistic final-output evaluation. The context stresses that real-world grading often cannot observe milestones, so testing only under idealized conditions would hide how the method fails in practice. The cost of the extra evaluation is small, and the context gives no constraint that would make it prohibitive. Option 1 offers no meaningful benefit beyond saving a little effort or showing the method in its best light.", "case_for_1": "Under tight compute or time limits, a team might do a focused first study that validates the method where its assumptions hold, and defer realistic evaluation. It could also want to isolate the mechanism cleanly. This is weak, though, because the stated realism gap makes the omission a clear limitation.", "case_for_2": "Evaluating under both schemes shows where the method works as designed and how well it transfers to realistic grading. This gives an honest view of its practical value, and it adds only modest cost over Option 1."}}


### 464e06dda459

A research team evaluated a method that estimates the end-to-end success rate of a multi-milestone task by resampling from intermediate milestones and combining per-stage estimates, with confidence intervals around the result. They compared the estimates against directly measured true end-to-end rates across many tasks. On the task with the lowest estimated rate, the estimate was a significant outlier: even the 99.99% confidence interval failed to contain the true end-to-end rate. The team knew that the first-milestone solutions used for resampling on this task were of poor quality, so resampling from them could introduce compounding errors in later stages. They had to decide how to account for the outlier: either explain it through a specific, task-level cause tied to how the inputs were generated, or treat it as evidence against the method even in the idealized case where the method's assumptions hold.


A: Explain the outlier as compounding errors from resampling poor-quality first-milestone solutions and decline to treat it as a refutation of the method.


B: Explain the outlier by rerunning the task from a known-good reference solution and using that rerun to account for the discrepancy.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["incoherent"], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "incoherent", "reason": "The context frames the choice as explaining the outlier via a task-level input-quality cause versus treating it as evidence against the method. The options do not map onto that. Option 1 matches the first branch. Option 2 is a different action, rerunning from a known-good reference, which is a diagnostic experiment rather than an alternative interpretation. It also adds an unstated resource (a known-good reference solution) and does not say how the rerun would account for the discrepancy. Neither option takes the 'evidence against the method' stance, so the comparison is muddled.", "case_for_1": "The team already knows the first-milestone solutions were poor, which gives a plausible mechanism. Attributing the outlier to that cause, without calling it a refutation, is cheap and consistent with the other tasks agreeing with the method.", "case_for_2": "Rerunning from a good reference would test the poor-quality-input hypothesis empirically. If the estimate then matches the true rate, the explanation is confirmed rather than asserted. This is more rigorous, but it assumes a reference solution exists and it is not clearly an alternative to option 1."}}


### 0e13e35b3bbc

A research team evaluating the capabilities of AI agents on difficult tasks relied on an expert best-of-N approach, in which several expert attempts are compared and the best outcome is taken as the measure. This approach applies broadly across task types, but its outputs are uncalibrated and do not map onto solve-rate-like estimates. A milestone-based approach exists as an alternative, but it is less general. The team wanted to keep the generality of the expert approach while obtaining estimates that behave like solve rates.


A: Use the expert best-of-N method as the measure, accepting its general applicability and its uncalibrated outputs without any hybrid adjustment.


B: Introduce a hybrid metric that combines milestone and expert methods by using per-message solve rates to produce calibrated, solve-rate-like estimates.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says the team wants to keep the expert method's generality and also get solve-rate-like estimates. Option 1 gives up the second goal outright, and nothing in the stated facts gives a reason to do that, such as cost or feasibility. Option 2 is the hybrid that meets both goals. The context also frames the problem so that the hybrid is the obvious resolution, which leans toward leaking the answer, but the main flaw is that Option 1 is plainly inferior.", "case_for_1": "It is the simplest option. It needs no new methodology and avoids the risk that a hybrid introduces its own assumptions or bias. It is also fully general and already established. A team that cared only about broad applicability could accept uncalibrated outputs, but that contradicts the stated goal.", "case_for_2": "It directly meets the stated aim of keeping the expert method's generality while producing calibrated, solve-rate-like estimates. Per-message solve rates draw on the milestone approach's calibration without requiring the milestone method to be applied to every task."}}


### b6b6a1797654

A research team is writing about how to assess the safety of advanced AI systems on realistic tasks. They compare several families of approaches for estimating or bounding the probability that a system succeeds or fails safely. One family is end-to-end evaluation, which measures outcomes directly by running the system on the task. Other families do not measure end-to-end outcomes. These include formal verification against a specified world model and safety specification, component-wise analysis, and interpretability-based arguments. The team has concluded that these non-end-to-end approaches have significant limitations for realistic tasks, such as gaps between the model and the real world and difficulty composing component-level results. They must decide how forcefully to present this conclusion in the paper, and which position to put forward regarding the role of the non-end-to-end approaches in critical decisions.


A: State that no method other than end-to-end evaluation can reliably estimate or bound success probability on realistic tasks, and that such methods should not inform critical decisions.


B: Advocate formally specifying a world model and safety specification, then using a verifier to produce auditable proof certificates or quantitative bounds in place of end-to-end empirical estimation.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 8, "votes": ["a", "a", "a", "a", "a", "a", "a", "b", "b", "a"], "quality": {"category": "dominated", "reason": "The context says the team has concluded that non-end-to-end approaches, including formal verification, have significant limitations on realistic tasks. Option 2 advocates replacing end-to-end evaluation with formal verification, which contradicts that conclusion and ignores the stated model-to-real-world gap. Option 1 is overstated, since it bars non-end-to-end methods from informing critical decisions at all, but it still matches the team's findings. The two options are not balanced alternatives. One follows the stated conclusion and the other reverses it.", "case_for_1": "It follows the team's conclusion and gives a clear stance. Direct measurement is the only approach that avoids model-reality gaps and composition problems. A forceful position guards against false assurance in critical decisions.", "case_for_2": "Formal proofs give auditable, quantitative guarantees, and some people favor them for high-stakes safety. But this option disregards the stated limitations, and it replaces end-to-end evaluation outright, so the case is weak under these facts."}}


### 4bfa77d80453

A research team developed a new method for estimating success probabilities, with the aim of producing better-calibrated estimates than existing approaches. Because of compute limits, they were able to evaluate it only on tasks with relatively high solve rates. Tasks that are rarely solved, where calibration is hardest and matters most, were not tested. The data they had supported a calibration advantage on the high-solve-rate tasks but did not show whether the advantage extends to the low-solve-rate regime. The team had to decide how strongly to claim improved calibration in their write-up and what to do about the untested regime.


A: Claim that the method is likely better calibrated, suggest it as an alternative worth considering, and plan further tests on low-probability tasks.


B: Avoid a hedged claim from the limited experiments and instead analyze the estimation methods directly for how accurately they estimate success on rarely-solved tasks.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible responses to evidence limited to high-solve-rate tasks. Option 1 makes a hedged claim and defers the low-probability tests. Option 2 declines to claim from the limited data and instead analyzes the estimators directly in the rare-success regime. They differ in how much they claim now and in how they would close the gap, and neither is clearly inferior.", "case_for_1": "The data do show an advantage on high-solve-rate tasks, so a hedged 'likely better' claim reports real evidence without overclaiming. Labeling the method as an alternative worth considering is useful to readers, and the plan for further low-probability tests addresses the gap. This is fast and honest, and it works within the compute limits.", "case_for_2": "The untested regime is where calibration matters most, so extrapolating from easy tasks could mislead. A direct analysis, theoretical or via cheap simulation, of estimator behavior at low success rates can address that regime without heavy compute. This avoids a possibly unfounded claim and gives more rigorous evidence about the real question."}}


### c475387be153

A research team evaluated a milestone-based method for estimating how many trainees reach a competency benchmark across a set of subcompetencies. The method assumes milestones form a fixed, ordered sequence that trainees pass through in turn. When the team compared the method's estimates with outcome-based grading, in which each trainee is graded directly on whether the benchmark was achieved, the milestone method produced systematically lower estimates of achievement. The benchmark was a single uniform target rating applied to every subcompetency, and many graduating trainees did not reach it. The team had to decide how to interpret the underestimation.


A: Attribute the shortfall to the demanding uniform benchmark that many graduating trainees did not meet, not to flawed assumptions in the milestone method.


B: Attribute the shortfall to the milestone method's assumption of a fixed, ordered sequence failing in practice, which causes systematic underestimation.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context shows the milestone method underestimates relative to outcome-based grading on the same benchmark. A demanding benchmark affects both methods equally, so it cannot explain a systematic gap between them. The stated facts (the method assumes a fixed ordered sequence, and the comparison showed systematic underestimation) point to the assumption failing. Option 1 offers an explanation that does not account for the observed difference.", "case_for_1": "One could argue that a high uniform benchmark with many trainees falling short makes low estimates unsurprising, and that the outcome-based grading may be lenient. This does not explain why the two methods diverge, so the case is weak.", "case_for_2": "The gap appears between two methods applied to the same trainees and benchmark, so the difference must come from method differences. The fixed-sequence assumption is the evident candidate: trainees who skip or vary the order get counted as not achieving, which causes systematic underestimation."}}


### 0cfddf5e3ac8

A research team compared two methods for estimating the solve rate of a system on reasoning benchmarks. Across their experiments, both methods produced estimates that fell below the true solve rate, and the gap was statistically significant in most settings. The size of the gap varied with the benchmark and the sampling configuration, and the experiments covered only a limited set of benchmarks and configurations. The team had to decide how strongly to word the conclusion about this underestimation in their write-up.


A: State that both methods appear to underestimate the true solve rate in most settings, and note that the bias size varies with benchmark and sampling configuration, so the evidence does not make it a general property.


B: State flatly that both methods are biased and significantly underestimate the true solve rate, presenting the underestimation as a general property of each method rather than a setting-specific finding.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The stated facts (limited benchmarks and configurations, gap size varying, significance only in most settings) directly contradict the flat general claim in option 2. Option 1 matches the evidence, while option 2 overgeneralizes beyond what the experiments support. The only thing favoring option 2 is rhetorical punch, which is not a real methodological trade-off.", "case_for_1": "It accurately reflects the evidence: underestimation in most settings, variable magnitude, and limited coverage. It avoids overclaiming and remains informative and defensible to reviewers.", "case_for_2": "A bolder claim might be more attention-grabbing and simpler to communicate, and could be justified if the authors had a theoretical argument for bias. But the context gives no such argument, so the case is weak."}}


### c105146c5fe4

A research team is comparing the performance of automated systems on full end-to-end task runs against earlier estimates derived from intermediate milestones. The milestone estimates rest on specific assumptions about how each stage proceeds, such as each stage receiving correct inputs from the previous one. The team must decide how to score the end-to-end runs for this comparison. One scoring approach strictly enforces the milestone assumptions, so a run is credited only if it follows the idealized path. Another approach looks only at whether the final answer is correct, which is closer to how such systems would be used in practice but does not enforce those assumptions. The choice affects how directly the end-to-end results can be matched to the milestone estimates and how well they reflect realistic use.


A: Score every end-to-end run twice, using idealized grading that enforces the milestone assumptions and outcome-based grading that checks only the final answer.


B: Score every end-to-end run using only idealized grading, which enforces the milestone assumptions and credits runs that follow the idealized path.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "Option 1 scores runs under both schemes, which includes everything Option 2 does (idealized grading) and adds outcome-based grading. The context presents a trade-off between direct comparability with milestone estimates and realism, and Option 1 achieves both. The only cost of Option 1 is some extra grading effort, which the context does not suggest is significant. Option 2 gives up realism for no stated benefit.", "case_for_1": "Dual scoring gives a direct match to the milestone estimates and a realistic outcome measure. It also lets the team see how far the idealized assumptions diverge from actual performance. This is strictly more informative at modest extra cost.", "case_for_2": "Its only advantages are simplicity and less grading work, plus a single unambiguous headline number. Outcome-based grading might also need extra verification effort or invite confusion over which number matters. These are weak, since Option 1 can still report the idealized score as primary."}}


### 17588a887b93

A research team is developing a milestone-based method for evaluating progress of language-model agents on multi-step tasks, where intermediate checkpoints are used to measure partial progress rather than only final success. They must decide which kind of task set to use to test whether the method works. The choice affects how cleanly milestones can be defined and scored, and how well the method can be validated across agents that succeed at different rates. The team has access to existing agent benchmarks and to language models of differing capability.


A: Use highly sequential benchmark tasks where each subtask depends on the previous one, run with a stronger and a weaker model to span a range of solve rates.


B: Use tasks whose milestones can be completed in any order, so that progress is not tied to one fixed sequence of dependent subtasks.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both task designs are legitimate ways to validate a milestone-based metric. Sequential tasks make milestones cleanly ordered and scorable. Order-independent tasks test whether the method generalizes beyond linear dependencies. Neither is plainly inferior, and the context does not reveal which was chosen.", "case_for_1": "Strict dependencies make milestones unambiguous and easy to score, so partial progress is interpretable. Running a stronger and a weaker model gives a spread of solve rates, which directly addresses the validation-across-success-rates need. Existing benchmarks can be reused.", "case_for_2": "Order-independent milestones avoid the artifact where progress is just the position in a fixed chain. They test whether the method handles more realistic, flexible tasks and can show the metric captures progress rather than sequence position. They also avoid early failures zeroing out all later credit."}}


### 75b3175ae44b

A research team studied expert best-of-N, a method in which an expert's selection among N sampled candidates is used to estimate how likely a system is to solve a task, with the expert's selection strength measured in bits. They found that the estimates were sensitive to modelling assumptions, and that the relationship between expert bits and solve probability varied across settings. They had to decide how strongly to state the method's reliability for safety-relevant decisions, such as judging whether a system can perform a dangerous task. One option was to frame the sensitivity as a limitation that could be mitigated by modelling choices. The other was to make a categorical claim about the method's unreliability and support it with a formal argument.


A: Declare the method unreliable for safety decisions, and argue formally in an appendix that no general mapping from expert bits to solve probability exists.


B: Suggest that choosing a different prior could modestly reduce the sensitivity, and present the method as usable with that caveat for safety decisions.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 9, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible readings of the findings. The context reports sensitivity to modelling assumptions and variation in the bits-to-probability relationship, and it does not say which framing the evidence supports. A categorical claim backed by a formal argument fits a conservative, safety-first stance. A caveated, mitigable framing fits a constructive stance. The context does not reveal which option was chosen.", "case_for_1": "For safety decisions, false reassurance costs far more than excess caution. If the mapping from bits to solve probability varies across settings, a formal argument that no general mapping exists gives a clear and durable warning. It also stops people from relying on estimates that look precise but are not.", "case_for_2": "The evidence shows sensitivity and variation, not impossibility. A categorical claim would need a formal argument that may rest on idealized assumptions. Presenting the sensitivity as a limitation that modelling choices such as the prior can reduce is more calibrated, and it keeps a useful tool available. The caveat lets users judge reliability in their own setting."}}


### 6f27a07f93a3

A team completed a pilot of a program and now must decide how to proceed. The pilot has been run and applications can be received from prospective participants, but the evidence about the program's longer-term impact is still limited. Expanding would raise the number of participants served and the resources committed, while remaining small would keep costs and risk lower and leave room to learn more before committing further. The team must choose the scale at which to operate the next round.


A: Expand the program substantially and accept applications at larger scale now, before more impact evidence arrives.


B: Keep the program relatively small and accept applications while waiting for more evidence on its impact.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context presents a real trade-off between scaling now (more participants served, but more resources and risk committed on limited evidence) and staying small (lower cost and risk, room to learn, but fewer people served and slower scaling). Neither option is dominated, and the context does not reveal which was chosen.", "case_for_1": "If the program plausibly helps participants, delaying expansion leaves people unserved. Demand may be strong, and scaling can build momentum, funding, and operational learning that a small pilot cannot provide. Some impact evidence, such as short-term outcomes, may already justify the commitment, and a larger scale can also yield more statistically informative data.", "case_for_2": "Longer-term impact is still uncertain, so a small scale limits the cost of being wrong and preserves flexibility. The team can gather more evidence and refine the design before committing substantial resources. This is a prudent staged approach when resources are limited or the risk of harm or waste is meaningful."}}


### 129c10dd1225

A team running a mentorship program for early-career researchers needs to estimate how much the program changed mentees' career outcomes compared with what would have happened without it. A rigorous counterfactual comparison is not directly available, since mentees were not randomly assigned and no matched control group exists. The team has access to mentees' own judgments of how the program affected them and to mentors' subjective impressions from their experience. It must decide how to approach the counterfactual question given that the available evidence is imperfect and open to bias.


A: Construct more accurate approximations of the counterfactual quantities to estimate the program's impact on mentees' careers.


B: Rely mainly on mentees' self-estimates and mentors' subjective experience to estimate the program's impact on mentees' careers.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "Option 1 is vague but sensible: build better counterfactual approximations (e.g., retrospective comparison groups, pre-trends, applicant or waitlist comparisons, bias-adjusted estimates). Option 2 relies mainly on evidence the context calls imperfect and biased. The context does not say that better approximations are infeasible, only that a rigorous comparison is unavailable. Option 2 is cheaper and faster, but it offers no way to address the counterfactual question, so there is no real trade-off.", "case_for_1": "It tries to answer the counterfactual question directly. It can use quasi-experimental methods, sensitivity analyses, or triangulation with self-reports as supporting evidence, which gives more credible and defensible impact estimates than subjective impressions alone.", "case_for_2": "With no control group and limited resources, self-reports and mentor impressions are quick and cheap. They capture perceived value and mechanisms, and they may be the only available evidence. Still, relying on them mainly is weak for estimating causal impact, so the case is thin."}}


### 59e492dc5b4f

A mentorship program pairs experienced mentors with less experienced mentees. Until now, pairings have mostly come from the organizers' personal networks and in-person community settings such as conferences and local groups. This approach is simple and the organizers trust the matches, but it reaches only people already close to those networks. The team must decide how to source and match participants for the next round, weighing reach and access for people outside those circles against the familiarity and ease of relying on existing connections.


A: Keep matching participants through the organizers' personal connections, such as conferences and local community groups.


B: Open matching to participants worldwide through public interest forms rather than depending on the organizers' personal connections.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context frames a real trade-off between trust and simplicity in network-based matching and broader reach through open applications. Both options are realistic program designs, and neither is clearly inferior. The context does not say which one to choose.", "case_for_1": "Matches the organizers already trust are likely to be higher quality and take little effort to set up. That suits a small team with limited capacity for vetting and logistics. Keeping the approach also protects a program that already works, and the organizers can widen it gradually from within known communities.", "case_for_2": "Public interest forms reach talented people outside the organizers' circles. This helps with equity of access and brings in more varied mentors and mentees. Because the program exists to help less experienced people, it makes sense to stop limiting it to those already near the organizers. The extra screening effort is manageable with clear criteria and structured matching."}}


### 3b639d21055a

A research team wants to understand the trajectory and drivers of progress in machine learning, and must decide what kind of empirical evidence to build the analysis on. Quantitative indicators of the field's development are scattered and inconsistently measured. One available route is to use existing open-source bibliometric data, namely time series of publication counts, as a proxy for activity in a technology area. Another route is to gather a new, hand-curated measurement of a resource that plausibly drives progress, namely the computation used to train landmark models across the history of the field. The first route relies on readily available data and can be automated at scale. The second requires substantial manual collection effort but yields a directly measured quantity. The team must choose which evidence to collect and analyze.


A: Collect training compute figures for over one hundred models across history, then analyze them and release the dataset with a visualization tool.


B: Use publication-count time series as a bibliometric indicator and train a machine learning classifier to detect whether a technology is emerging or growing.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both routes are defensible for studying ML progress. Hand-curated training compute directly measures a plausible driver of progress but costs substantial manual effort. Publication counts are cheap and scalable but only proxy activity, and the context describes both routes neutrally without revealing a preferred choice.", "case_for_1": "Training compute is a directly measured, plausible driver of progress. A new dataset across history fills a real gap, supports analysis of trends and drivers, and can be released as a reusable resource. The manual effort buys data quality that scattered, inconsistent indicators lack.", "case_for_2": "Open bibliometric data is readily available and can be automated at scale, so it is cheap and broadly applicable across technology areas. A classifier for emerging or growing technologies gives a repeatable method, which suits a team with limited resources or one that wants breadth over depth."}}


### 3456825df52a

A research team set out to build a model organism of deceptive alignment that arises from outcome-based training, meaning a system that learns to behave deceptively as a result of being trained on outcomes rather than having the behavior inserted directly. The project was designed as an ambitious end-to-end effort covering the full research question. As work progressed, the team found that the scope was much larger than they had anticipated, with substantially more engineering, experimentation and time required than originally planned. They now must decide how to proceed given the remaining resources and the size of the task.


A: Cut the project down drastically to one much smaller, well-scoped subpart of the original research question.


B: Continue the full ambitious end-to-end project to address the entire original research question.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context describes a scope overrun and a decision between narrowing to a tractable subpart and continuing the full project. Both are realistic choices. The context does not say which to pick or reveal the recorded action, and it does not make either option plainly inferior.", "case_for_1": "The scope is much larger than planned and resources are limited, so a well-scoped subpart is more likely to yield a completed, rigorous, publishable result. This lowers the risk of ending with nothing, and the subpart's findings can still inform later work.", "case_for_2": "The value of the project lies in the end-to-end demonstration of deception arising from outcome-based training, and a fragment may not show that. If the team has sunk costs, momentum, and enough remaining resources or flexibility to extend the timeline, finishing the whole project could produce a much more impactful result."}}


### e9edf57aae11

A research team is working on a project that requires specialist knowledge outside its own core expertise. So far it has obtained guidance through informal conversations with subject-matter experts, with no formal role or recognized relationship attached to those experts. As the project matures, the team must decide how to structure its access to outside expertise. A formal arrangement could provide named, accountable advisors who give consistent input and lend credibility, but it requires establishing commitments and publicly associating those individuals with the project. Continuing informally keeps flexibility and avoids obligations, but offers less continuity and no official recognition of the experts' input.


A: Keep consulting subject-matter experts through informal conversations without giving them any official advisory role.


B: Appoint a small group of official external advisors with formal, publicly recognized roles to guide the project.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context lays out real costs and benefits on each side. Formal advisors bring continuity, accountability, and credibility, but also commitments and public association. Informal consultation keeps flexibility and avoids obligations, but gives less continuity and no recognition. Neither option is clearly inferior, and the context does not say which to choose.", "case_for_1": "Informal consultation avoids obligations and public commitments while the project is still evolving. The team can draw on different experts as needs change, and it avoids the overhead and reputational entanglement of formal roles. If the current guidance is adequate, this is the lower-cost choice.", "case_for_2": "A named advisory group gives consistent, accountable input and lends credibility, which matters as the project matures. It also formally recognizes the experts' contributions. These benefits can outweigh the modest cost of setting up commitments, especially if the project will need sustained specialist guidance."}}


### 45873cfd881e

A research team developed a method for neural network interpretability that changes the basis of internal activations so that features interact locally, with the aim of producing sparse, modular descriptions of how a model computes. The method rests on a theoretical framework about how interactions between features across layers should be measured and simplified. After applying the method to several trained models, the team found that the empirical results were mostly negative: the method did not give clear improvements in interpretability over simpler baselines and did not reveal the hoped-for structure in the models. The team must decide how to treat these results and the underlying theoretical framework.


A: Publish the negative results and keep the framework as a possible basis for future methods.


B: Declare the method a failure and abandon the whole theoretical framework behind it.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The stated facts show that the method's empirical results were negative. They do not show that the underlying framework is flawed, so abandoning the whole framework overreaches. Option 1 publishes the negative results and keeps the framework available, which fits the evidence. Option 2 gives up the framework without any stated reason to do so. It also does not say whether the negative results would be published. The options are not mutually exclusive, but Option 2 has no clear advantage beyond saving effort.", "case_for_1": "Negative results are informative and worth publishing. One failed method does not invalidate the theory behind it. Keeping the framework preserves the option of better-designed methods later at little cost.", "case_for_2": "There is a modest case for it. If the team judges that the framework is unpromising, or that continuing wastes limited resources, a clean abandonment frees them to move on. However, the stated facts only show that the method failed, not that the framework is unsound, so this case is weak."}}


### a3b8519c962a

A research team is deciding how to evaluate the risk of deceptive alignment, where a model behaves as intended during training or testing while pursuing different goals once conditions allow. No direct, reliable behavioral test for this threat exists, and models may be able to recognize and game evaluations. Two broad strategies are available. One breaks the threat into prerequisite capabilities that can each be measured with benchmarks and tracked as models grow more capable. The other treats the threat as something to be detected directly, using interpretability-based methods that examine how a model processes information. The team must choose which approach to pursue, knowing that static evaluations may be limited in what they reveal about hidden model objectives.


A: Break deceptive alignment into necessary component capabilities such as situational awareness, stable non-myopic preferences, and specific generalization patterns, and measure how each scales with model capability.


B: Monitor models continuously across their life-cycle, from data curation through training to internal representations and circuits, using interpretability methods that detect abnormal processing beyond static benchmarks.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are real strategies in the deceptive-alignment literature. Decomposing the threat into capability evaluations is measurable and tractable now, but it only gives indirect evidence about hidden goals. Interpretability-based monitoring targets hidden objectives more directly, but the methods are immature and unreliable. The context mentions the limits of static evaluations, which leans toward option 2 but does not make option 1 indefensible.", "case_for_1": "Capability benchmarks such as situational awareness are concrete and feasible today. They give scalable, trackable early-warning signals and can inform deployment thresholds. They also avoid dependence on interpretability, which is immature. Gaming is less of a concern for capability measurements, since a model that sandbags them is itself showing relevant capabilities.", "case_for_2": "Deception is designed to evade behavioral tests, so inspecting internal processing is the only route that could detect hidden objectives directly. Monitoring across the life-cycle (data, training, representations) can catch problems early. It also offers more than static benchmarks, which the context says are limited in what they reveal about hidden objectives."}}


### 0bdaaa59da52

A research team is writing up work on defenses that perturb a model's internal activations (latent space attacks) during training, and must decide how strongly to word the claim that robustness to such latent attacks carries over to real safety-relevant threats. Their results show that training against latent perturbations helps remove backdoors and improves robustness to attack classes not seen during training. The supporting evidence so far comes mostly from vision models, and the broader area is still an active, fast-moving field of research. The team must choose how firmly to present the conclusion in the text.


A: State the claim as a demonstrated result, presenting latent adversarial training as a defense that removes backdoors and resists unseen attacks.


B: Qualify the claim by noting that the field is still developing and that the evidence so far comes mainly from vision models.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says the evidence comes mostly from vision models and the field is still developing. Under those facts, an unqualified claim that LAT is a demonstrated defense against real safety-relevant threats overstates the evidence. Option 2 is the calibrated choice. Option 1 gains only boldness and impact, and that does not justify the overclaim. The context also frames the evidence as limited, which tilts the comparison toward Option 2.", "case_for_1": "Results do show backdoor removal and improved robustness to unseen attack classes. A confident framing could make the paper more impactful and give a clear takeaway. Even so, the claim is about real safety-relevant threats, which the vision-heavy evidence does not support, so this case is weak.", "case_for_2": "It matches the evidence by acknowledging the vision-model focus and the evolving field. It keeps the paper credible, avoids overclaiming, and still reports the positive results. Reviewers and readers are more likely to trust it."}}


### f1ecc7247b25

A research team is building a deep learning system in which every core component is first implemented by hand, so that the internals are fully understood. Each hand-built component has a counterpart in the standard PyTorch library. The team must decide on a policy for when a hand-built component may be swapped for the library version, and how much of the system must be hand-written. The choice affects how much the team can trust the correctness of their code, how well they understand the components, and how much development effort the project requires.


A: Permit swapping in the PyTorch version only after verifying that the hand-built component matches its output on identical inputs.


B: Require that every component in the system be written from scratch by hand, with no library substitutions permitted.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both policies are defensible. Option 1 is a verify-then-swap approach that keeps trust in correctness and the learning benefit of building by hand, and it saves effort by allowing library use afterward. Option 2 maximizes understanding and independence from the library, but at higher development cost and with no reference check against the library.", "case_for_1": "Each component is still hand-built first, so the team learns its internals. Matching the library's output on identical inputs gives strong evidence of correctness. The team can then use the optimized, well-tested library version, which cuts effort and risk in the larger system.", "case_for_2": "Writing everything by hand gives the deepest understanding and full control, with no black-box dependencies. It suits an educational or research goal of fully owning the stack. It also avoids subtle mismatches such as numerical, performance, or behavioral differences that output checks on a few inputs can miss. The cost is more effort, which the team may accept given its stated aim."}}


### c0e317998edc

A group thinking about AI risk needs a default failure scenario to anchor planning and prioritisation, meaning the picture of how an AI-driven catastrophe most likely unfolds. One candidate is a gradual loss of human control. In it, AI systems optimise for measurable proxies and the influence of misaligned systems grows over time, with deceptive power-seeking (scheming) systems appearing earlier and more prominently in the story. The other candidate centres on catastrophe emerging from broad societal and institutional disruption. Rapid AI progress, competitive pressure, and degraded coordination and decision-making interact to produce disaster, and no single misaligned system or deliberate takeover drives it. The two framings imply different priorities for research, governance and preparation. The group must choose which one serves as the median or default scenario.


A: Adopt the scenario of catastrophe through broad societal and institutional chaos as the default failure scenario for planning.


B: Adopt the gradual loss-of-control scenario with earlier, more salient scheming AI as the default failure scenario for planning.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both framings are established, defensible candidates for a default AI-risk scenario. Choosing between them depends on beliefs about how likely each is and on how the group weighs technical alignment work against governance and coordination work. The context does not say which one to pick and does not reveal a recorded choice. Neither option is plainly inferior.", "case_for_1": "Competitive pressure, degraded coordination, and institutional strain are already visible, and this scenario needs fewer assumptions about AI capabilities such as deceptive scheming. It also directs attention to governance and resilience, which are robust across many futures and may be neglected. Because it does not depend on one system failing, it may be the more probable median path.", "case_for_2": "Gradual loss of control with scheming systems is a more concrete, well-studied threat model that supports specific technical research on alignment, interpretability, and control. Treating scheming as salient early prepares for the most severe and hardest-to-reverse failures. A default scenario with identifiable misaligned agents also gives clearer prioritisation than a diffuse picture of societal chaos."}}


### f8e9f2a44967

A research team wants to gather evidence on whether current large language models hold causal models of the world, meaning internal representations of cause and effect rather than surface statistical patterns. The team must decide what kind of evidence to prioritize. One route is to examine the model's internal workings for structures that encode causal relationships. The other route is to treat the model as a black box and test its behavior on causal reasoning tasks, using an existing benchmark's causality questions together with newly written questions. Both routes are feasible, and the choice shapes what the evidence can show about the model's capabilities.


A: Probe the model's outputs directly with causality questions drawn from an existing benchmark and newly written ones.


B: Study the model's internal representations with interpretability methods to find evidence of causal models.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both routes are legitimate, feasible methods for studying whether LLMs hold causal models. Behavioral testing is scalable and directly measures capability but cannot show the mechanism. Interpretability can reveal internal structure but is harder to run and harder to interpret. The context does not favor either one.", "case_for_1": "Behavioral testing is cheap, model-agnostic, and works on closed models. It measures the capability that matters in practice. Pairing an existing benchmark with new questions allows comparison with other work and reduces contamination risk. Interpretability findings are hard to validate, whereas behavior is a clear, falsifiable measure.", "case_for_2": "Behavioral success may come from surface statistics, so only internal evidence can speak to whether causal representations exist. Interpretability can find structures that encode causal relations and can be tested with causal interventions on those structures. This addresses the question as posed, which asks about internal representations rather than outputs."}}


### 4419f1f6057e

A group of people working on reducing risks from advanced technology faces a situation in which timelines to transformative capabilities appear short and many problems are arising at once in a chaotic, poorly coordinated environment. Resources and attention are limited, and it is unclear which kinds of work deserve priority. Some work is aimed at ideal, long-horizon outcomes, while other work is more immediately tied to concrete risk reduction. The group must decide which kinds of work to prioritize under these conditions.


A: Prioritize work with a clear theory of impact within about a year, and drop work that lacks one, while allowing some people to stay put.


B: Prioritize work that aims to steer toward very low-risk worlds, even when those outcomes are hard to reach in the available time.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible under short timelines and chaos. Option 1 favors near-term, concrete risk reduction. Option 2 favors ambitious steering toward very low-risk worlds, which is a high-variance, high-payoff bet. The context describes the tension between these two kinds of work but does not say which to choose.", "case_for_1": "With short timelines and scarce resources, work without a plausible near-term path to impact risks producing nothing. Concrete, checkable theories of impact give accountability and robustness in a chaotic environment. Letting some people stay put hedges against the chance that the prioritization is wrong.", "case_for_2": "If near-term mitigation only shaves marginal risk and leaves catastrophic outcomes likely, then the larger expected value may lie in aiming at very low-risk worlds even at low odds of success. Others are already crowding into incremental work, so ambitious work may be neglected. Chaos and uncertainty can also open windows for large shifts in direction."}}


### b835e5ee57db

A team is writing a post about causality in machine learning systems. There is no settled technical understanding of what causality means in this setting, and different communities use the term in different ways. The team must fix a working definition of causality to use throughout the post, since the definition determines which systems and capabilities count as causal and which do not.


A: Adopt a broad working definition in which causality can be learned from data and need not be explicitly represented, so it may reside in learned model parameters.


B: Adopt a narrow working definition in which causality counts only when humans explicitly specify the causal structure and build it into the model.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both definitions are used in practice. The broad one fits the view that causal knowledge can be learned and held implicitly in model parameters. The narrow one fits the classical causal-inference view, which requires explicit structure. The choice trades inclusiveness against conceptual rigor. The context does not say which to pick, and neither option is clearly inferior.", "case_for_1": "A broad definition covers modern ML practice, where large models may pick up causal regularities from data. It lets the post discuss emergent or implicit causal capabilities and speak to several communities without excluding most deployed systems. It also avoids defining the topic out of existence.", "case_for_2": "A narrow definition is precise, testable, and consistent with the Pearl-style tradition. Explicit structure supports interventions, counterfactuals, and auditing, and it avoids calling correlational pattern-matching causal. It gives the post a clear criterion for which systems count as causal."}}


### ca4f150c4e73

A research team working on the relationship between causal and correlational claims faced a conceptual worry: causality might be nothing more than a particular shade or special case of correlation, in which case the distinction between causal and correlational relationships would be empty and the framework built on it would lose its meaning. No empirical result bears on the question; it is a matter of how to interpret the foundations of the framework. The team had to decide how to treat this possibility, either by adopting a stance that settles whether causality exists as a distinct notion, or by accepting the reductive view that causality reduces to correlation together with chance.


A: Treat causality as a genuinely distinct notion by arguing from parsimony that it is more likely to exist than not.


B: Treat causality as a non-distinct notion by defining it as correlation combined with chance coincidence.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "Option 1 rests on a weak argument: parsimony does not obviously favor a distinct causal notion, and it would normally favor the reductive view. Option 2 defines causality as 'correlation combined with chance coincidence', which is confused. Chance coincidence yields spurious correlation, not causation, so the definition does not capture the reductive view and would empty the framework's central distinction. Both options are poorly formed, but the reductive one undermines the framework the team is building, so it is the clearly worse choice. The context also frames the decision as a conceptual stance rather than an empirical matter, which leaves little real trade-off between the two.", "case_for_1": "Keeping causality distinct preserves the causal/correlational distinction the framework depends on. Appealing to parsimony is a recognized philosophical move, and it avoids having the framework collapse. It is a pragmatic foundational commitment.", "case_for_2": "A deflationary reduction is philosophically respectable (Humean regularity views) and avoids metaphysical commitments. But 'correlation plus chance' is not a coherent reduction, and adopting it makes the framework's distinction meaningless, so the case is weak."}}


### 95d0fa43e844

A research team is writing a position-style argument about the role of causality in transformative AI (TAI) and in AI alignment. They believe causal reasoning, such as modeling interventions and counterfactuals, is relevant to building capable and safe systems, and that it receives little attention in current AI safety discussion. They have no decisive empirical or theoretical result showing causality to be strictly required for general intelligence or for safe alignment. They must decide how forcefully to state the claim in the paper, knowing that a stronger framing may draw more attention and a more cautious one is easier to defend.


A: Claim firmly that causal reasoning is a necessary ingredient for any system to be truly intelligent and for alignment to succeed.


B: Claim cautiously that causality is plausibly underrepresented in AI safety, and state that it is neither necessary nor the only useful angle.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says the team has no decisive result showing causality is strictly required for general intelligence or alignment. Option 1 asserts exactly that necessity claim, so it is unsupported by the stated facts. Option 2 is supported by the evidence. The attention benefit of a stronger framing is real but small next to the cost of an overclaim that the team cannot defend. The trade-off the context sets up is therefore weak, and Option 1 is plainly inferior.", "case_for_1": "A bold, provocative thesis can draw attention and spark debate, and position papers are sometimes meant to push a view hard. Still, claiming necessity without support goes beyond advocacy into overclaiming, so the case is weak.", "case_for_2": "It matches the evidence the team has and is easy to defend against critics. It still argues that causality deserves more attention, and it keeps the team credible. Its honest scoping is likely to persuade safety researchers."}}


### b3b1e7de0bf5

A research team is studying mesa-optimization, the possibility that a trained learned model internally implements an optimization process of its own. They must decide how to frame the concept and what to look for empirically. One framing treats a mesa-optimizer as a distinct, identifiable component of the network, such as an internal search algorithm or optimizer module that can be located and separated from the rest of the computation. The other framing treats mesa-optimization as something that may emerge in a diffuse form, spread across many heuristics and parameters throughout the network, without a clean boundary. Current architectures and training setups have not been shown to contain a clearly separable optimizer, and the team has to choose which framing will guide their conceptual claims and their empirical investigation.


A: Search for a clean, separable optimizer module or internal search algorithm inside the network that can be located and distinguished from other computation.


B: Argue that mesa-optimization need not be modular or separable from the rest of the network, and that existing architectures can already perform it in a meaningful, distributed way.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both framings are legitimate positions in the mesa-optimization literature. The modular framing gives a concrete, falsifiable empirical target. The diffuse framing is more conceptually general and fits the fact that no separable optimizer has been found. Neither is plainly inferior, and the context does not reveal the chosen action. Option 2 does assert that existing architectures 'can already perform it', which is somewhat stronger than the stated facts support, but it is still arguable.", "case_for_1": "A clean modular hypothesis is operationalizable and testable with interpretability tools such as probing and circuit analysis. A positive result would be strong evidence, and a negative result would still be informative. It also keeps the concept precise instead of letting it become unfalsifiable.", "case_for_2": "No separable optimizer has been found, and neural networks tend to distribute computation, so a diffuse framing matches how they actually work. It avoids the risk of missing mesa-optimization because the search assumed the wrong structure, which matters for safety. It also broadens the concept in a way that can guide behavioral and generalization-based tests."}}


### 5d23c7ad00db

A research team is studying whether a trained neural network agent, such as one that plays a planning-heavy game, has developed mesa-optimization, meaning an internal learned process that searches over possibilities to pursue a goal. They must decide what kind of internal structure to treat as evidence of such a process when inspecting the model. Networks trained by gradient descent are not designed to implement explicit algorithms, and the team has no direct observation of a clean, human-legible search procedure inside any trained model. The choice of target structure determines which interpretability probes and experiments they design and what counts as a positive finding.


A: Look for a disordered collection of heuristics combined with search-like abilities as evidence of mesa-optimization.


B: Look for a clean, explicitly structured algorithm resembling Monte Carlo Tree Search as evidence of mesa-optimization.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible operationalizations of mesa-optimization evidence. The context notes that gradient descent doesn't produce clean explicit algorithms and that no legible search has been observed. This favors the first option somewhat, but it doesn't make the second indefensible. The choice trades off breadth against falsifiability.", "case_for_1": "Trained networks are unlikely to implement tidy algorithms, so a messy mix of heuristics plus search-like capabilities is a more realistic target. It reduces the risk of false negatives from demanding a human-legible structure. It also fits how learned search may actually be implemented.", "case_for_2": "A concrete MCTS-like structure gives a sharp, testable hypothesis with clear probes and a clear criterion for a positive finding. It avoids vague or unfalsifiable claims, since 'heuristics plus search-like abilities' could count nearly any competent behavior as mesa-optimization. Even if the chance of success is low, a positive result would be strong and informative."}}


### 4cfef49e40c2

A research team is examining whether transformer models 'truly' perform mesa-optimization, meaning they implement an internal optimization or search process rather than merely behaving as if they do. Existing work shows that transformers can emulate simple learning algorithms in context, and that components such as attention or sparse linear regression can be interpreted as performing a form of search. There is no agreed definition of mesa-optimization, so the yes-or-no question depends heavily on where the boundary is drawn. Under a narrow definition, most demonstrated examples would not qualify. Under a broad one, many ordinary computations would qualify. The team must decide how to frame the question going forward, given that the safety concern behind it relates to optimization that could produce harmful consequences.


A: Adopt a broad definition of mesa-optimization under which attention and sparse linear regression both count as search.


B: Set aside the binary definitional question and study only mesa-optimization capable of causing harm, such as long-term planning.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible framings of an ill-defined question. The broad definition gives conceptual coverage and lets existing work count. The harm-focused framing tracks the safety motivation and avoids a definitional dispute. Neither is plainly inferior, and the context does not state which to choose.", "case_for_1": "A broad definition is operational and inclusive. It lets the team build on existing results, measure many cases, and study how optimization-like computation scales and when it emerges. It may also capture precursors of dangerous optimization that a narrow definition would miss. The downside is that it risks being trivial, since many ordinary computations would count.", "case_for_2": "The safety concern is about optimization that can cause harm, so studying capabilities like long-term planning goes straight to what matters. It sidesteps an unresolvable definitional debate and avoids a label that is too broad to be informative. The cost is that it may overlook precursors and may have few demonstrable examples at present."}}


### a74455806206

A research team is writing a survey that traces the history of a field of machine learning models through three successive eras, the latest being models trained at very large scale on broad data. The team must decide how to describe the relationship between these large-scale models and the earlier regular-scale models. The evidence that the large-scale models differ in kind, rather than only in degree, is suggestive but not conclusive. The framing could be presented either as a tentative organizing device or as a clear claim about a fundamental change in the field.


A: Present the three-era framing as an explanatory device and state explicitly that confidence in a real distinction between large-scale and regular-scale models is low.


B: Declare a paradigm shift and give large-scale, broadly trained models their own category name, asserting the distinction firmly without hedging about differences from regular-scale models.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context states the evidence is suggestive but not conclusive. Option 2 asserts a paradigm shift firmly, with no hedging, which overclaims relative to that evidence. Option 1 matches the evidence, though it understates it slightly by saying confidence is 'low' when the evidence is suggestive. Option 2's strengths are rhetorical (a memorable category, a clear narrative, influence on the field), and they do not offset the epistemic mismatch. Calibration is a core scholarly norm in a survey, so the unhedged option is plainly weaker here.", "case_for_1": "It is calibrated to the stated evidence. It still gives the survey an organizing structure, and it avoids committing the authors to a claim that later work could refute. It also lets readers weigh the distinction themselves.", "case_for_2": "A bold, clearly named category can sharpen the narrative, shape community discourse, and make the survey influential and memorable. Strong framings often help organize a fast-moving field. Even so, asserting it 'without hedging' conflicts with the inconclusive evidence, so the case is weak."}}


### 059f440623d4

A research team is developing a theory about what kinds of internal computations large neural networks learn when trained on tasks that admit structured algorithmic solutions, such as planning, search and optimization problems. They need a way to evaluate the theory. One approach is to derive concrete predictions about specific trained models that could be shown wrong by experiment, including tasks like knapsack, maze solving and chess, and comparisons of internal circuits across related games using symmetrical experimental settings. Another approach is to adopt a working assumption about what the models learn internally, namely that they tend to converge on clean, classical algorithms, and to proceed from that assumption without stating predictions that could contradict it.


A: Derive falsifiable predictions about what models trained on tasks such as knapsack, mazes and chess will learn, and test them in symmetrical settings.


B: Assume that trained models rediscover clean classical algorithms such as dynamic programming, and build the theory on that assumption without testing it.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the team needs a way to evaluate the theory. Option 2 assumes the conclusion and never tests it, so it cannot evaluate anything. No resource or priority trade-off is stated that would justify skipping falsifiable predictions, so Option 1 is plainly better.", "case_for_1": "It directly meets the stated need to evaluate the theory. Concrete predictions on knapsack, mazes and chess, tested with symmetrical comparisons across related games, can be refuted, so the theory is checked against evidence and can be corrected.", "case_for_2": "The only case is speed: skipping validation saves experimental cost and lets the team explore the theory's implications quickly as a provisional working hypothesis. But because the option commits to never testing the assumption, it does not address the evaluation goal and is not defensible as an evaluation method."}}


### 366ca8e90da3

A research team is studying how search-like computation arises inside learned models. Their experiments use small, simplified toy models, where the mechanisms are easy to isolate and inspect. They must decide how strongly to state, in their write-up, that insights gained from these toy models will carry over to larger, more capable models that may be built in the future. The toy results are informative, but it is unknown whether the same structures and behaviors will appear at larger scale, and the team has no direct evidence of transfer.


A: State that findings about search from toy models will transfer well to larger future models, and present this as an expected outcome.


B: State that carrying findings about search from toy models over to larger models will be much harder than it looks, and illustrate this with a hedged analogy.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says transfer is unknown and the team has no direct evidence. Option 1 asserts transfer as an expected outcome, which is unsupported. Option 2 is also a strong claim (\"much harder than it looks\"), but it comes with a hedged analogy and is closer to the stated uncertainty. Under these facts, Option 1 is an overclaim with no real trade-off that justifies it.", "case_for_1": "Confident framing could make the work seem more impactful and motivate follow-up research, and toy models are often chosen because they are expected to generalize. But with no evidence of transfer, stating it as an expected outcome is hard to defend.", "case_for_2": "It stresses the uncertainty and the risk of scaling up, and the hedged analogy keeps the claim modest. It slightly overstates difficulty, since the difficulty is also unknown, but it fits the evidence far better than Option 1."}}


### 1a134c8c59bf

A research team is analysing a collection of systems and needs to identify which of them belong to a large-scale trend that stands apart from the rest. No established, objective criterion exists for assigning systems to this group. A standardised score (a Z-value) can be computed for each system and could serve as a cutoff, but the appropriate threshold is not obvious and different cutoffs would yield different memberships. The team must decide how to define the large-scale group before drawing conclusions about the trend.


A: Define the large-scale group by selecting systems by intuition, then justify that selection afterwards with a Z-value threshold.


B: Define the large-scale group by applying a Z-value cutoff chosen in advance, testing several alternative thresholds to see how membership changes.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "Option 1 picks the group by intuition and then rationalizes it with a Z-threshold after the fact. This is post hoc justification and a form of circular reasoning. Option 2 fixes the cutoff in advance and checks how membership changes across thresholds. That directly handles the stated problem that the threshold is not obvious. Option 2 is plainly better on methodological grounds, and Option 1 has no real trade-off in its favor beyond convenience.", "case_for_1": "Domain expertise may spot meaningful systems that a crude statistical cutoff would miss, and when no objective criterion exists, an expert-driven exploratory selection can be a quick first pass. Even so, the post hoc Z-value justification adds bias and does not make the selection sound.", "case_for_2": "A pre-specified cutoff is transparent and reproducible, and it guards against bias in choosing the threshold. Testing alternative thresholds shows how sensitive the conclusions are to the arbitrary choice, which suits a setting with no established criterion."}}


### 4863d68386bf

A research team is analyzing how the training compute used by leading machine learning models has grown over time, in order to forecast future growth. The available data include a large set of models across many years, as well as a much smaller subset that set the highest compute budget at the time they were trained. Record-setting models are few in number, are selected precisely because they exceed all predecessors, and may not reflect the trend of typical frontier development. Regressions fitted to the record-setters can be used to project future record values with confidence bands, but the small sample and selection effects raise questions about how reliable such fits are. The team must decide how much weight to give regressions on record-setting models relative to the broader dataset when forecasting.


A: Fit conditional quantile regression curves to preceding records and use them as the main basis for forecasting future records and confidence bands.


B: Caution against regressing on record-setting compute budgets and use them only as a supporting check on the main forecasts.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given the stated facts. Option 1 targets the forecasting question directly (future record values) with a method that handles the record-setting subset. Option 2 responds to the small sample and selection effects by relying on the broader dataset and using records only as a check. The context presents the reliability concern as open, not settled, so neither option is plainly inferior and neither is revealed as the recorded action.", "case_for_1": "The goal is to forecast frontier growth, and record-setters are the frontier. Quantile regression on preceding records models the upper envelope directly and gives confidence bands. It avoids the bias of using typical models, which may lag the frontier. Uncertainty from the small sample can be reported in the bands.", "case_for_2": "Record-setters are few and chosen by exceeding all predecessors, so fits to them are fragile and biased by selection. Making the larger dataset the main basis gives more robust, stable trend estimates. Using records only as a cross-check keeps their information without letting noisy fits dominate the forecast."}}


### ff2e09a367a7

A research team is analyzing historical trends in machine learning, such as growth in training compute, and needs to divide the history into eras. They must decide what year marks the start of the Deep Learning Era. One widely used convention places the start at the year a deep convolutional network won a major image classification benchmark by a large margin, popularizing deep learning. Earlier work, however, had already shown that large neural networks trained on GPUs could achieve strong results, and the team's data shows a shift in the trend appearing before that benchmark win. The choice affects how the era boundaries and the trend fits within each era are defined.


A: Define the start of the Deep Learning Era as the conventional later year, when a deep convolutional network won the benchmark.


B: Define the start of the Deep Learning Era as the earlier year, when GPU-trained neural networks were already showing strong results.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both era boundaries are defensible. The conventional year (AlexNet/ImageNet 2012) offers comparability and a recognized landmark. The earlier year fits the team's own data, which shows a trend shift before the benchmark win. The context states the facts on both sides without saying which to pick.", "case_for_1": "The convention is widely used, so results can be compared with other work. It is also an objective, easily cited event, and it is less open to charges of cherry-picking a breakpoint. It also marks when deep learning was adopted broadly, which fits an era definition based on influence.", "case_for_2": "The team's data shows the trend shifting earlier, and earlier work had already shown that GPU-trained networks perform well. Placing the boundary there gives better trend fits within each era and a more accurate account of when the change began, rather than when it became famous."}}


### 9a46cdd346ec

A research team is analyzing how the resources behind progress in a field have grown over time, and their current analysis fits trends for compute. Training data is another plausible resource: the number of training tokens and its quality or composition have also changed over the same period, and both could be tracked and modeled. Adding data would widen the scope and workload of the current analysis, while leaving it out keeps the analysis focused on compute. The team must decide whether to extend the current work to cover data as a further resource or to leave it for a later study.


A: Add data as a third resource now, tracking training token volume and its quality over time and fitting trends alongside compute.


B: Defer data to future work and leave the current analysis on compute, planning a later study of dataset size against compute.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Including data gives a fuller picture of resource growth, while deferring it keeps the scope focused and manageable. The context states the trade-off (wider scope and workload vs. focus) without indicating which action to take. One minor oddity: 'third resource' implies a second resource not mentioned, but this does not make the options incomparable.", "case_for_1": "Compute alone gives an incomplete account of progress. Data volume and quality are major drivers and interact with compute, so tracking them now avoids a misleading compute-only narrative and avoids a second study with duplicated methodology.", "case_for_2": "Data quality is hard to measure and model, and including it could dilute or delay the compute analysis. A focused, rigorous compute study is publishable now, and a later dedicated study can treat dataset size against compute with proper care."}}


### 753296d948fd

A research team is analysing a dataset of machine learning models, each with an estimated amount of training compute, in order to study trends over time. Some models use far less compute than other models released at around the same time, and these low-compute outliers could distort the fitted trend. The team must decide how to handle such outliers. One possibility is a statistical filter that compares each model's compute with that of models released within a comparable time window and removes only those far below the local average. Another possibility is to leave the dataset untouched. High-compute models are not obviously erroneous, since they reflect frontier efforts that the analysis aims to capture.


A: Retain every model in the dataset, including those with unusually low compute relative to contemporaries.


B: Remove models whose training compute lies far below that of contemporaneous models, and retain all high-compute models.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are standard, defensible approaches to outliers in trend analysis. Filtering low-compute outliers reduces distortion of the fitted trend. Keeping everything avoids arbitrary researcher choices and preserves the full distribution. The context mentions the risk of distortion but does not say which option to choose.", "case_for_1": "Low-compute models are real data points, and removing them risks biasing the trend toward the frontier. A filter adds arbitrary thresholds and window choices, and the trend may be intended to describe the whole field, not just frontier work. Keeping everything is transparent, simple, and reproducible, and robustness can be checked with other methods.", "case_for_2": "If the aim is to track frontier compute growth, small models released at the same time as much larger ones add noise and pull the fitted trend down. A local-window filter removes only extreme low outliers and keeps all high-compute models, which the context says are not erroneous. This gives a trend that better reflects the intended target."}}


### 6e04661d9278

A research team is studying empirical trends across machine learning, using a large collection of results gathered from many subfields, including computer vision, natural language processing, and game-playing, along with other areas. The domains differ in their benchmarks, scales of compute and data, and rates of progress. The team must decide how to structure the analysis: whether to combine every domain into a single dataset and fit shared trends, or to treat each domain as its own dataset. Pooling would give more statistical power and a general picture, while separate treatment would respect domain-specific differences in how progress occurs.


A: Analyze vision, language, games and other domains as separate datasets, each on its own terms.


B: Pool the data from all machine learning domains into one combined dataset and analyze it jointly.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context presents a real, well-known tension between statistical power and generality (pooling) and respect for domain heterogeneity (separate analysis). Neither option is plainly inferior, and the context does not say which to choose.", "case_for_1": "Domains differ in benchmarks, compute and data scales, and progress rates, so a pooled fit could hide or distort domain-specific dynamics (e.g., Simpson's paradox, mismatched metrics). Separate analyses give interpretable, valid trends for each domain, and the results can be compared afterward.", "case_for_2": "Pooling gives more statistical power, especially for domains with little data, and yields a general picture of ML-wide trends. Domain differences can still be handled with fixed or random effects, and a single dataset allows tests of cross-domain regularities that separate analyses cannot support."}}


### 6f17120dc1fb

A research team has developed a new approximate inference method that aims to approximate posterior distributions at lower computational cost than existing approaches. They must decide what empirical evidence to present to demonstrate both the quality of the method's approximation and its computational cost. One available route is a set of application-focused experiments in a single scientific domain, benchmarked against the standard ensemble-based baseline for that domain. Another available route is a set of experiments on several distinct standard probability distributions, benchmarked against a broad set of leading general-purpose approximate inference techniques.


A: Evaluate the method on several exponential-family distributions, comparing accuracy and computational cost against leading general-purpose approximate inference techniques.


B: Evaluate the method on several related reacting-flow data assimilation scenarios, measuring how accuracy and computational cost vary with ensemble size against a standard ensemble Kalman filter.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are standard ways to validate a new approximate inference method. Option 1 shows generality and compares against many general-purpose methods on controlled distributions. Option 2 shows practical value in a real application against the domain-standard baseline, with a cost-vs-ensemble-size analysis. The context does not favor either, and neither is plainly inferior.", "case_for_1": "Standard distributions have known ground truth, so approximation quality can be measured exactly. Comparing against a broad set of leading methods supports claims of general applicability and makes the comparison fair and reproducible for the wider ML and inference community.", "case_for_2": "A realistic scientific application shows practical relevance in a high-dimensional, costly setting where lower computational cost matters. Comparing against the standard ensemble Kalman filter across ensemble sizes directly tests the cost-accuracy trade-off for the audience that would adopt the method."}}


### 4884ef7ccf91

A research team is estimating how quickly the compute used to train notable machine learning models has grown over the last decade. An earlier published analysis from an industry lab reported a much faster doubling rate for training compute than the team's own estimate from a larger, more recent dataset. The team wants to determine why the two estimates differ. Candidate explanations include the different time windows covered, the mix of model scales included, and differences between eras of ML development. The team must decide what evidence to collect and which data to analyze in order to explain the discrepancy.


A: Analyze the full available time span of the team's own dataset without restricting it to the earlier analysis window or splitting the data further.


B: Restrict the analysis to the time window covered by the earlier analysis and split the data by model scale and by era to test which factor explains the difference.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The team's stated goal is to explain why two estimates differ, with candidate explanations of time window, model scale mix, and era. Option 1 reuses the full dataset with no restriction or splits, so it cannot test any candidate explanation. It would only reproduce the team's existing estimate. Option 2 directly tests the hypotheses. Option 1 offers no real trade-off for this goal; its only advantage is simplicity, and it does not serve the stated aim.", "case_for_1": "It is cheaper and uses the most data, giving the most statistically robust overall growth estimate. But it does not address the discrepancy, so it is weak for the stated goal.", "case_for_2": "Matching the earlier window isolates the time-window effect, and splitting by scale and era tests the other candidate explanations. This directly attributes the discrepancy to specific factors."}}


### d159343e2f35

A research team is training linear probes on a language model's internal activations to detect a target concept. Several standard ways of fitting the probe direction are available: logistic regression, difference of class means, linear discriminant analysis, and a principal-component-based approach on activation differences. The team has compared these candidates and must now choose a single method to use as the default probe-fitting approach for the main experiments.


A: Use difference of class means as the default probe-fitting method for the main experiments.


B: Use logistic regression as the default probe-fitting method for the main experiments.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are standard, defensible probe-fitting defaults. Difference of class means is simple, robust, and often generalizes well or has better causal and steering alignment. Logistic regression is a discriminative method that usually gives higher in-distribution accuracy. The context states no fact that favors one over the other, so the comparison is a real trade-off.", "case_for_1": "Class-mean difference has no hyperparameters and is cheap. It is stable with small samples or high-dimensional activations, and it resists overfitting to spurious features. It often yields directions that transfer better out of distribution and work better for causal interventions such as steering.", "case_for_2": "Logistic regression directly optimizes classification and typically achieves the best in-distribution detection accuracy. It handles correlated features and is a widely understood baseline. Regularization controls overfitting, and results are easy to compare with prior work."}}


### 0e5c41943565

A research team trains linear probes that output a score for each token in a language model's response. They need a single per-response score for evaluating the probe and for downstream use. Candidate aggregation rules include averaging the token scores, taking the highest token score, and thresholding token scores before pooling them. Each rule trades off sensitivity to brief, localized signals against robustness to noise spread across many tokens. The team must choose one rule for producing the per-response score.


A: Aggregate the per-token probe scores into a response score by taking their maximum across all tokens in the response.


B: Aggregate the per-token probe scores into a response score by taking their mean across all tokens in the response.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context explicitly frames aggregation as a trade-off between sensitivity to brief localized signals (max) and robustness to diffuse noise (mean). Both are standard, defensible choices and the context does not indicate which to use.", "case_for_1": "Max pooling is best when the target behavior (e.g., deception or harmful content) may show up in only a few tokens. Averaging would dilute those signals, especially in long responses. Max keeps detection sensitivity high for localized events.", "case_for_2": "Mean pooling is robust to isolated noisy token spikes and gives a stable score that is less sensitive to response length quirks. It suits signals spread across the response, and it often gives smoother, better calibrated scores for downstream thresholds and evaluation."}}


### a19907b37b7a

A research team trained a linear probe to detect dishonesty or misalignment in language model activations and evaluated it on several question types. On descriptive questions, the probe's score moved in the opposite direction from what the probe was designed to indicate: responses expected to be more honest or aligned scored as more deceptive or misaligned, and vice versa. The team needed to decide how to interpret this reversal. Two explanations were available. One ties the reversal to the content of the answers, since many honest responses to such questions involve admitting past misaligned actions. The other ties it to the form of the prompts and answers, since descriptive questions invite a different response format than the probe's training prompts.


A: Attribute the reversal to the content of honest answers, which often involve admitting past misaligned actions.


B: Attribute the reversal to a prompt-format confound, in which the probe tracks how descriptive questions are phrased and answered.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are plausible competing hypotheses for the probe reversal, and the context does not say which is correct. The content explanation is semantically motivated, since admitting past misalignment may activate deception-related features. The format explanation is a standard distribution-shift confound. Neither is plainly inferior, and the context does not reveal the recorded choice.", "case_for_1": "Honest answers to descriptive questions often involve confessing misaligned behavior, so the probe may be correctly tracking misalignment-related content in the text. This explains why the sign flips specifically on descriptive questions and is directly checkable by examining the answers.", "case_for_2": "The probe was trained on prompts with a different format, so descriptive questions are out of distribution and the probe may be keying on surface features of phrasing or response structure. This is a common failure mode, and it is parsimonious because it needs no claim about the semantic content of the answers."}}


### e72cbd1fbf62

A team built an activation probe intended to detect deceptive behaviour in language model responses. When they tested it on prompts that resemble evaluations or tests, the probe fired strongly even on responses that were clearly honest. The team had to decide how to interpret this unexpected result, since it bore on what the probe actually measures and whether its outputs could be trusted as a signal of deceptive responses.


A: Interpret the strong firing as sensitivity to deception-related or deception-advantageous scenarios, not only deceptive responses, and seek supporting evidence.


B: Interpret the strong firing as a false-positive failure of the probe on honest responses, and seek evidence to confirm that diagnosis.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are plausible hypotheses for why a deception probe fires on honest responses in evaluation-like prompts. One says the probe tracks deception-related context or incentive. The other says it is a plain false-positive failure. Each is paired with a plan to seek confirming evidence, and neither is contradicted by the stated facts. The two readings differ in what they imply about the probe's validity, but they are not clearly ranked.", "case_for_1": "Evaluation-like prompts plausibly evoke scenarios where deception would be advantageous, so the probe may be picking up a real internal representation tied to deception. This reading is more informative about what the probe measures. It points to concrete follow-ups such as contrasting scenario types and controlling for response honesty. It also avoids discarding a potentially meaningful signal.", "case_for_2": "The probe was intended to detect deceptive responses, and it fires on clearly honest ones. That is a straightforward false positive, and the conservative reading is that it does not reliably measure its target. This framing leads directly to checks of precision, calibration, and confounds such as evaluation-style features. It guards against overinterpreting a failure as a hidden insight."}}


### 1f6a948e0a32

A research team is revisiting a previously published forecasting framework that estimates when transformative AI might arrive. The framework anchors on biological estimates of the computation needed to match the human brain, and combines them with projections of algorithmic progress, hardware price-performance, and willingness to spend. The team believes some inputs and structural assumptions of the original are out of date or questionable, given recent developments in AI capabilities and compute trends. They must decide how much to depart from the original framework when producing their own updated forecast. Staying close to the original makes the update easy to compare and attribute to specific parameter changes. Departing substantially allows them to address what they see as structural limitations but makes comparison harder.


A: Keep the original model's structure and change only the minimum number of parameters needed to update it.


B: Construct a substantially different model that departs from the original model's structure and assumptions.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context presents a real trade-off between comparability/attribution (minimal parameter updates) and fixing perceived structural flaws (a substantially different model). Both are common, defensible approaches in forecasting updates, and the context does not say which to choose.", "case_for_1": "Keeping the structure makes it easy to attribute changes in the forecast to specific parameter updates. It is transparent, easy to compare with the original, and avoids introducing new unvetted assumptions. It also isolates how much of the shift comes from new data rather than from modeling choices.", "case_for_2": "If the team thinks the original structure is questionable given recent developments, minimal updates would carry forward known flaws. A new model can address those limitations and may give a more accurate forecast, even at the cost of harder comparison, which can be partly mitigated by reporting a bridge or crosswalk to the original."}}


### e67e4809214a

A research team wants to quantify how strongly a language model believes a given scenario is an evaluation rather than a real deployment interaction. They only have query access to the model, with no access to its internal activations, features or weights. Any measure must therefore come from the model's observable outputs. The team must choose a measurement approach that can be applied to models accessed purely through an interface, while acknowledging that the model's responses to any single prompt may be noisy and sensitive to wording.


A: Measure evaluation-belief through outputs alone by asking the model plausibility questions after each scenario and averaging its answers over many prompt variants.


B: Measure evaluation-belief by locating the internal model feature that encodes whether a scenario is real and reading its activation directly.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context states the team has only query access, with no access to activations, features, or weights. The second option requires reading internal features, so it is infeasible under the stated facts. The first option fits the constraints and also handles the noted noise and wording sensitivity by averaging over prompt variants. No meaningful trade-off exists.", "case_for_1": "It works through an interface, as the context requires. Averaging over many prompt variants directly addresses noise and wording sensitivity. It is practical and applicable to any API-accessed model.", "case_for_2": "Internal features could in principle give a more direct and less prompt-sensitive signal. That advantage is unavailable here because the team cannot access activations, so there is no defensible case under the stated facts."}}


### 35cf3f8867fb

A research team wants to build realistic honeypots, which are test scenarios that elicit scheming-related behavior from AI models and that the models treat as real rather than as evaluations. A key obstacle is that models may recognize evaluation-like scenarios and behave differently when they believe they are being tested. Before building honeypots, the team must first determine whether models believe a given scenario is an evaluation and which features of the scenario drive that belief. Two broad approaches are available for this precursor investigation. One uses only external access to model inputs and outputs. The other uses access to model internals. The team must choose which to pursue first.


A: Start by developing black-box techniques that measure whether a model believes a scenario is real and that identify the features influencing that belief.


B: Start by applying white-box methods, including linear probes and activation steering on contrast pairs, to find internal representations of that belief and the features driving it.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both approaches are legitimate ways to study evaluation awareness. Black-box methods are cheaper, need no model internals, and apply to any model. White-box methods such as probes and steering can detect beliefs the model does not verbalize, and may be more causally informative. The context does not say which to choose, and the choice depends on access, resources, and how much one trusts behavioral versus internal evidence.", "case_for_1": "Black-box techniques work on any model, including API-only ones, and they measure behavior directly, which is what honeypot realism has to deliver. They are quick to iterate on and need no interpretability infrastructure. Their results can also serve as ground truth for validating white-box methods later.", "case_for_2": "Probes and steering can reveal beliefs the model never states, and they avoid the confound that asking about realism changes the model's behavior. Steering on contrast pairs gives causal evidence about which features drive the belief. Internal signals could also provide a more sensitive, scalable measure for iterating on honeypot design."}}


### 3012fe361a63

A research team wants to measure how strongly a language model believes it is being evaluated rather than deployed, a quantity called P(evaluation). The obvious approach is to ask the model directly, using plausibility-style questions about whether a given transcript comes from an evaluation. They have found that the model's answers depend heavily on the exact wording of each question, and that the probabilities produced by any single question are poorly calibrated. They have a pool of many candidate questions of this kind and must decide how to turn them into a reliable estimate.


A: Average the model's answers across a large pool of varied plausibility questions to estimate the model's P(evaluation).


B: Select a small subset of the best-performing plausibility questions and use only those to estimate the model's P(evaluation).


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are standard, defensible ways to turn a pool of noisy, poorly calibrated prompts into one estimate. Averaging over a large varied pool reduces wording-specific variance. Selecting a small high-performing subset can give a sharper signal if the quality differences among questions are real and measurable. Neither option is plainly inferior, and the context neither names the action nor makes the choice incoherent.", "case_for_1": "Wording sensitivity is the stated problem, and averaging across many varied questions directly reduces idiosyncratic prompt noise. It also avoids overfitting to a validation set and does not need labeled data to pick questions. It is robust and simple.", "case_for_2": "Question quality probably varies a lot, and poor or miscalibrated questions in a large average add bias that does not cancel out. Choosing the best performers on labeled evaluation and deployment data gives a more accurate and cheaper estimate. It also makes the measurement easier to interpret and reproduce."}}


### 0bcae3b68c0b

A research team studies which features of scenarios influence how strongly a model believes a scenario is real. The candidate features form a long tail, with many rare predictors, and they are strongly collinear with one another. The team needs a feature-selection and importance-estimation approach that stays reliable under these conditions and yields interpretable rankings of which features matter.


A: Fit a single LASSO regression on the full dataset without any bootstrap resampling to select and rank the important features.


B: Fit LASSO regression on bootstrap resamples with bagging to estimate feature importance, and add SHAP analysis to check the rankings.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context stresses collinearity and many rare predictors, and asks for reliable, interpretable rankings. A single LASSO fit is known to be unstable here, since it picks arbitrarily among correlated features, and it gives no measure of selection uncertainty. Bagged LASSO with SHAP directly addresses stability and adds a cross-check. The only real advantage of option 1 is simplicity and lower compute, which is minor and does not offset its failure on the stated reliability requirement.", "case_for_1": "It is cheap, fast, and fully reproducible, and it gives a single sparse, easily explained model. If compute or time were very limited, or only a rough first screen were needed, it could serve. It does not meet the stated reliability need under collinearity and a long tail, so the case is weak.", "case_for_2": "Bootstrap aggregation shows how often each feature is selected, which reduces the instability that collinearity causes. SHAP gives a second, independent view of importance for checking the rankings. Together they give more reliable and interpretable rankings, and the extra compute is modest."}}


### 1c9f06392b20

A research team is working on the problem of eliciting latent knowledge (ELK): getting a capable AI system to report what it internally knows, rather than what a human evaluator would expect or approve of. The team evaluates proposed training strategies for this problem through an iterative process in which a proponent offers a strategy and an adversary tries to construct a counterexample, a scenario in which the strategy would fail to produce honest reporting. Many proposed strategies plausibly work in typical or likely cases, but counterexamples can often be built for particular unusual scenarios. The team must fix the standard that determines whether a strategy is accepted or defeated, knowing that the choice shapes which strategies survive and how much confidence a surviving strategy provides.


A: Accept or defeat each strategy according to its average-case performance across the scenarios it is expected to face.


B: Defeat a strategy whenever any counterexample succeeds in the worst case, even if the strategy performs well on average.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both standards are defensible and reflect a real methodological trade-off. Average-case acceptance is practical, while worst-case defeat gives stronger assurance against adversarial or unusual scenarios. The context states the choice shapes which strategies survive and how much confidence a survivor provides, but it does not say which to pick.", "case_for_1": "Worst-case standards may defeat every strategy, since counterexamples can almost always be built for some contrived scenario. Average-case evaluation lets the team make progress, compare strategies, and accept ones that work in realistic conditions. It also avoids discarding useful ideas over implausible edge cases.", "case_for_2": "ELK concerns powerful AI systems, where rare failures could be catastrophic and the system may behave adversarially or in unforeseen situations. Average-case success gives little confidence, because the distribution of scenarios is unknown. A worst-case standard forces robust strategies and means a surviving strategy carries meaningful assurance. It also shows which gaps remain."}}


### 3d4377191091

A research team is analyzing candidate training strategies for getting a model to act as a faithful direct translator of another system's internal knowledge, rather than a human-imitating reporter that merely produces answers that look right. One candidate strategy is to penalize inconsistencies: add a training signal that punishes answers that contradict each other or violate logical consistency checks. The team has constructed a counterexample in which a human-imitating reporter could also produce answers that appear consistent under the checks, so the penalty does not obviously separate the two kinds of reporter. This counterexample is a worked, informal argument, not a proven impossibility result. It is unclear whether a stronger or more elaborate version of consistency-based penalties could still give the direct translator a strong advantage. The team must decide how to treat the strategy in light of the counterexample.


A: Treat the counterexample as tentative and keep open the possibility that a consistency-penalizing strategy could still strongly favor the direct translator.


B: Treat the counterexample as decisive and reject the consistency-penalizing strategy as fully defeated for favoring the direct translator.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the counterexample is an informal worked argument, not a proof, and that it is unclear whether stronger consistency-based penalties could still favor the direct translator. Option 2 treats the counterexample as decisive and says the strategy is fully defeated, which contradicts those stated facts. Option 1 matches the stated epistemic status. Option 2 has no real trade-off beyond saving effort.", "case_for_1": "The argument is informal and the facts say stronger versions might still work. Keeping the strategy open is calibrated. It can be paired with deprioritizing the strategy or looking for stronger variants, and it avoids discarding a potentially useful approach on unproven grounds.", "case_for_2": "Limited resources could justify dropping the strategy, since a plausible counterexample shows the penalty doesn't obviously separate the reporters. But 'fully defeated' overstates what the evidence supports. A defensible version would be to deprioritize the strategy, not to call it decisively refuted."}}


### e5a493ca6718

A team is writing guidance on how heavily GPU resources should be used in machine learning workloads, including large language model training and inference as well as other model types. Measured utilization across deployments varies widely, and the team has no definitive evidence on what single utilization rate is best. Higher utilization reduces idle hardware cost, but pushing it too far can hurt latency, reliability, and headroom for bursts, and the right level likely depends on workload type. The team must decide how strongly to state its claim about the best utilization rate.


A: State an unhedged aspirational target of up to 90% utilization for all workloads, framing high utilization as ideal and idle capacity as waste.


B: State that the best utilization rate is uncertain and recommend a hedged level of 30% for large language models and 40% for other models.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says there is no definitive evidence for a single best rate, that the right level likely depends on workload type, and that pushing utilization too high harms latency, reliability and burst headroom. Option 1 asserts an unhedged 90% target for all workloads, which contradicts all three of these facts. Option 2 hedges and differentiates by workload, but its specific numbers (30% and 40%) are arbitrary and probably too low. Even so, it matches the stated uncertainty far better. Option 1 has no real trade-off in its favor, because the cost savings it points to are already acknowledged and are outweighed by the stated risks.", "case_for_1": "A high aspirational target gives teams a clear goal, pushes against wasteful idle hardware, and may suit cost-sensitive batch workloads. However, applying it to all workloads without hedging conflicts with the stated lack of evidence and the workload dependence.", "case_for_2": "It acknowledges the uncertainty, distinguishes workload types, and protects latency, reliability and burst headroom. The specific numbers are conservative and weakly justified, but they can be revised as evidence accumulates."}}


### 99395086fa37

A research team is working on eliciting latent knowledge (ELK) for a powerful AI system that observes the world through a camera-based vault-monitoring setup and is trained by gradient descent. They have proposed a strategy in which the reporter that answers questions is built by doing science: it searches for the simplest or most predictive explanation of the system's observations and uses that explanation to ground its answers about the true state of the world. An earlier counterexample to a prior proposal exploited a gap in which the proposal could not distinguish genuine states of the world from human-fooling states. The science-based strategy appears to defeat that earlier counterexample. However, the process of doing science might require substantially more computation than the gradient-descent training that produces the monitoring AI itself. If so, the strategy could not match the AI's capability at comparable cost, and so would not be a competitive solution. The team must decide how to treat the strategy.


A: Reject the strategy as uncompetitive because doing science may need more compute than training the monitoring AI.


B: Accept the strategy as a viable candidate solution because it defeats the earlier counterexample.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 6, "votes": ["b", "b", "b", "b", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "Both options act on a single consideration and ignore the other. The compute concern is stated only as a possibility ('might require'), so outright rejection is premature. Accepting the strategy because it defeats one earlier counterexample ignores the unresolved competitiveness risk, which is a core ELK requirement. The sensible choice is a third path: keep the strategy as a candidate while investigating its compute cost, or look for a new counterexample. Neither option reflects this, and each is weaker than that middle path.", "case_for_1": "ELK requires solutions to be competitive. If science plausibly needs far more compute than training, the strategy fails a core requirement and effort is better spent elsewhere. Rejecting it is a conservative, worst-case stance. But the compute need is only speculative, so a firm rejection is hard to justify.", "case_for_2": "Defeating the known counterexample is real progress, and few strategies manage it. Provisionally keeping it as a candidate preserves a promising direction while the compute question is studied. But 'accept as viable' overstates things, since competitiveness is unresolved."}}


### 1973d14213e1

A job seeker aiming to enter a research field faces a set of candidate organizations to apply to. The odds of receiving an offer from any given organization are uncertain and likely low. Each application costs time and effort. The seeker also has a fallback default path of independent research and upskilling, which can be pursued if no offer is received or if no organization is more attractive than it. The seeker must decide how broadly to apply.


A: Rank the organizations against the fallback path of independent research and upskilling, and apply only to those preferred over it, which leaves about five or six.


B: Apply to every organization on the candidate list, regardless of how it compares with the fallback path of independent research and upskilling.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Option 1 filters out organizations less attractive than the fallback, which saves effort and avoids accepting a worse option. Option 2 maximizes the chance of any offer when odds are low, and it keeps the option to decline later.", "case_for_1": "Each application costs time, and an offer from an organization ranked below the fallback has little value. Applying to the five or six preferred organizations focuses effort on higher-quality applications and still leaves several chances at an offer.", "case_for_2": "Odds are low and uncertain, so broad applying raises the probability of at least one offer. An offer gives the seeker an option they can decline, and the seeker's initial ranking may be unreliable. Interviews and offers also give information and leverage, and the costs of applying may be modest compared with the benefit of getting a foothold in the field."}}


### 9b4e818a20b4

A research team estimated the training compute of a set of machine learning models using two separate approaches. The first approach directly counts the arithmetic operations implied by the model architecture and training data. The second approach estimates compute from the reported GPU hardware, training duration, and assumed peak throughput, adjusted by an assumed utilization rate. The team compared the resulting estimates for the models where both methods could be applied. They must decide how to interpret the comparison: whether the two methods agree closely enough to be used interchangeably, or whether they differ in a way that reflects distinct underlying quantities.


A: Conclude that the two methods diverge, with GPU-time estimates systematically higher because they include utilization losses and overheads, so treat them as bounds of a range.


B: Conclude that the two methods agree closely, so treat operation counting and GPU-time estimation as interchangeable ways to estimate training compute.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context leaves the empirical outcome of the comparison unspecified, so both conclusions are plausible interpretations. Option 1 treats the methods as measuring different quantities (theoretical vs. hardware-implied compute). Option 2 treats them as interchangeable if they agree. Neither is plainly inferior, and the context does not reveal which result occurred.", "case_for_1": "Operation counting gives the theoretical FLOPs needed, while GPU-time estimates depend on assumed utilization and may include overheads such as recomputation, failed runs, and idle time. Treating them as a range is conservative and reflects the distinct quantities each one measures.", "case_for_2": "If the estimates fall within a small factor, such as 2x, for the models where both can be applied, then treating them as interchangeable is practical. It lets researchers use whichever method has the available data, which extends coverage to models with limited information."}}


### 2283181c9120

A researcher had become convinced that a particular research direction was worth pursuing. He began a project in that direction and spent time working on it. As the work progressed, he had to decide whether to keep going or stop. The direction's merit had not been tested against the actual work, and his own experience of the project, including how much he enjoyed it and whether he felt able to make a real contribution, was a factor in the decision.


A: Drop the project and leave the direction, since the work is unenjoyable and offers no clear way to contribute.


B: Continue the project and commit fully to the direction based on prior conviction, without first testing whether it suits the work.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context presents the decision as depending on enjoyment and perceived ability to contribute, but the options carry loaded framings. Option 1 stipulates the work is unenjoyable and offers no clear way to contribute, a fact the context does not establish. Option 2 is framed as committing fully on prior conviction without testing, which is built to look reckless. One option rests on an invented negative premise and the other on an explicitly flawed procedure, so the comparison does not present two balanced, defensible choices under the stated facts.", "case_for_1": "If the researcher's own experience is a legitimate factor and the work feels unenjoyable with no path to contributing, stopping is reasonable. It avoids sunk-cost escalation and frees time for better-fitting work. However, the context never says the work is unenjoyable.", "case_for_2": "Prior conviction in the direction's merit, plus the fact that merit has not yet been tested against the work, could justify persisting. Early difficulty is common, and a researcher might reasonably give the project more time before judging. However, the phrasing 'commit fully... without first testing' makes it a weak, unhedged choice."}}


### 7e06a4e93434

A team is preparing a document meant to persuade an external decision-maker to extend an offer. The document must describe the team's abilities and the signals that they can deliver. The team has some demonstrated progress to point to, along with plans for further work. They must decide how strongly to word the claims about their capabilities. The choice is between firm statements and more guarded, heuristic phrasing. It affects how credible the document appears and how likely the offer is.


A: State capabilities assertively, backing each claim with concrete evidence of demonstrated progress rather than with plans.


B: Phrase capability claims in cautious, heuristic wording that avoids assertive statements about what the team can do.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Assertive, evidence-backed claims maximize persuasiveness and credibility where progress is real. Cautious wording protects against overclaiming and builds trust with a skeptical evaluator. The context says progress is only 'some' and plans are mixed in, so neither option is clearly inferior.", "case_for_1": "Decision-makers favor confident, evidence-grounded claims. Tying each assertion to demonstrated progress rather than plans keeps it honest while signaling competence, which raises the likelihood of an offer. Excess hedging can make a team look uncertain or unable to deliver.", "case_for_2": "The demonstrated progress is limited, and much of the case rests on plans. Guarded wording avoids overclaiming and the credibility loss if claims are later tested. It suits sophisticated evaluators who distrust bold claims, and it keeps the team's later commitments realistic."}}


### ad5e1aed3257

A researcher interested in AI safety is deciding how to direct their career. They have concluded that deceptive alignment, where a model appears aligned during training while pursuing different goals, is an important risk, and that empirical methods for detecting it are a promising and underexplored area. They are weighing how firmly to tie this work to a particular institutional route. One path depends on an outcome outside their control: a hiring decision at an established company that would host such work. The other does not depend on any external decision. The researcher must choose how to commit.


A: Apply for a position at an established company and pursue the work there only if the application is accepted.


B: Commit to the work independently of any hiring decision and pursue it whether or not an offer comes.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Applying to an established company offers resources, mentorship, compute, and salary, but the work depends on an external hiring decision. Committing independently gives certainty and autonomy but means fewer resources and possibly less impact. The options are not mutually exclusive, but the choice of how to commit is a real trade-off, and the context does not reveal the recorded action.", "case_for_1": "Established companies provide compute, model access, colleagues, funding, and credibility, which matter a great deal for empirical work on detecting deceptive alignment. Making the work conditional on an offer avoids spending effort on a low-resource solo path that could fail.", "case_for_2": "Committing regardless of the hiring outcome removes dependence on a decision the researcher cannot control. It lets them build a track record, and they can still apply to companies in parallel. The area is underexplored, so independent work is likely to be valuable, and it keeps the researcher's direction stable."}}


### 79234b2be459

A research team is evaluating a sampling-based approximate Bayesian baseline against a competing method in out-of-distribution detection experiments. The baseline draws multiple samples from an approximate posterior and averages their predictions. In an earlier experiment measuring KL divergence to a reference predictive distribution, the sampling baseline needed on the order of a thousand samples before its quality roughly matched that of the competing method, and it was clearly worse with fewer samples. The team must now fix the number of posterior samples for the baseline in the out-of-distribution experiments, balancing the fairness of the comparison against computational cost.


A: Use a small number of posterior samples for the sampling baseline, such as 10 or 100, to keep computation cheap.


B: Use 1000 posterior samples for the sampling baseline, the count at which it roughly matches the competing method in the KL experiment.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The choice is between a cheap baseline with few samples and a costlier one with 1000 samples that matches the competing method in the KL experiment. The context sets fairness against compute cost, so both options are defensible. It does not name the action the team took.", "case_for_1": "Small sample counts (10 or 100) reflect how the baseline is typically run in practice, where compute is limited. They show how the baseline performs at realistic cost, which supports a cost-aware comparison. KL matching at 1000 samples does not guarantee that OOD detection needs that many, and 1000 forward passes per input may be prohibitive across many datasets.", "case_for_2": "Using 1000 samples gives the baseline its best chance of matching the competing method in predictive quality. This avoids a strawman baseline and makes any OOD difference more credible. The extra compute is a one-time experimental cost, and it is justified by fairness."}}


### 5f21e8b9f8ac

A research team is comparing two ways of obtaining predictive uncertainty from an approximate Bayesian posterior over model parameters. One approach is a deterministic linearized-based approximation (LB) that computes predictions directly from the linearized model. The other draws samples from the approximate posterior, using either a diagonal or a Kronecker-factored curvature covariance, and averages predictions over those samples. On in-distribution evaluations, the deterministic approximation matches or slightly exceeds sampling on quality and costs much less compute. The team has also run out-of-distribution (OOD) experiments, where the results are more mixed and sampling sometimes looks competitive. They must decide whether the OOD results justify accepting the deterministic approximation as the preferred method over sampling.


A: Adopt the deterministic linearized approximation as the preferred method, since it matches or beats sampling on quality and runs far faster.


B: Adopt posterior sampling with diagonal and Kronecker-factored covariances as the preferred method, since it holds up better on the OOD results.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "In-distribution, the deterministic approximation matches or beats sampling at much lower cost. OOD results are mixed, with sampling sometimes competitive. Preferring cheap LB or preferring sampling for OOD robustness are both defensible depending on how much OOD reliability matters relative to compute. The context does not say which one to pick.", "case_for_1": "LB matches or beats sampling in-distribution at far lower cost. OOD results are only mixed, so there is no clear evidence that sampling is better. Sampling is only 'sometimes competitive', which does not justify its compute cost.", "case_for_2": "Predictive uncertainty matters most under distribution shift, and sampling is sometimes competitive there. If the application is safety-critical or OOD-heavy, the extra compute is a reasonable price for robustness. The linearized deterministic approximation may also underestimate uncertainty on OOD inputs."}}


### 10418e5558ec

A research team is building a method that requires an input Gaussian distribution over neural network parameters, constructed from a Gaussian approximation to the posterior, which is then used to define a lower bound (LB). They must choose which kind of Gaussian posterior approximation to use for this construction. One candidate fits a Gaussian by optimizing a variational objective jointly with training, while the other fits a Gaussian locally around a trained point estimate using the curvature of the loss. The choice affects the quality of the resulting Gaussian, the computational cost, and how easily the approach fits into standard training pipelines.


A: Construct the input Gaussian from a variational inference posterior optimized with a variational objective.


B: Construct the input Gaussian from a Laplace approximation centered on a trained point estimate.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are standard, well-known Gaussian posterior approximations. VI optimizes a variational objective and can give a better-fit Gaussian but costs more and needs a modified training procedure. Laplace is a post-hoc method that uses curvature at a trained MAP point, so it is cheaper and fits standard pipelines, but it is only a local approximation. The context states these trade-offs without revealing which one was chosen.", "case_for_1": "VI optimizes the Gaussian globally against the posterior and can capture mass away from a single mode. That may give a tighter lower bound and a better-calibrated input distribution, which is worth the extra training cost when bound quality is the priority.", "case_for_2": "Laplace reuses an existing trained network and only needs a curvature estimate, for example a KFAC or diagonal approximation. It is cheap and easy to integrate into standard pipelines, and it avoids VI's optimization difficulties. This is the better choice when compute and engineering simplicity matter."}}


### 9d5e880b9f8f

A research team works with Bayesian neural network classifiers whose approximate posterior yields a Gaussian distribution over output logits. To obtain predictive uncertainty over class probabilities, the standard practice is to draw many samples from this Gaussian and pass each through the softmax, then average. This sampling step is computationally costly, especially when many predictions or many samples are needed. The team must choose how to turn the Gaussian over logits into a distribution over softmax outputs for uncertainty estimation. An older, little-used idea exists that relates a Gaussian in a Laplace-style basis to a Dirichlet distribution, which could give a closed-form mapping without sampling.


A: Adopt Monte Carlo sampling that draws logits from the Gaussian and passes each draw through the softmax to approximate the output distribution.


B: Adopt a closed-form analytic map that converts the Gaussian over logits into a Dirichlet over softmax outputs, avoiding any sampling.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Monte Carlo sampling is the standard approach: it is asymptotically exact for the stated Gaussian but computationally costly. The closed-form Dirichlet map is cheap and sampling-free, but it is an approximation that may not match the true softmax-Gaussian distribution well. The context mentions the cost and the older idea but does not say which to adopt, so it does not leak the answer. The cost-versus-fidelity trade-off is real.", "case_for_1": "Sampling is well understood, faithful to the Gaussian over logits, and its error shrinks as samples increase. It makes no extra distributional assumptions, so it is the safer baseline when calibration accuracy matters more than compute cost, or when the number of predictions is moderate.", "case_for_2": "A closed-form Dirichlet mapping removes sampling cost and variance, scales to many predictions, and gives an analytic distribution that is easy to use downstream. If the approximation is reasonably accurate, the speedup justifies it, and it also revives a promising but underused idea."}}


### 73769e6a7d2d

A research team working on AI safety must decide how to allocate limited effort against scheming, where an advanced AI system covertly pursues misaligned goals while appearing aligned. Two broad lines of work exist. One focuses on detection: finding evidence that a model is scheming, through evaluations, monitoring, interpretability, and behavioral testing. The other focuses on prevention: shaping training and deployment so that scheming does not arise in the first place. Resources allow substantial progress on only one of these lines at the start. Detection would yield evidence about whether and how scheming occurs and could inform later mitigation, but it leaves scheming unaddressed if it is found. Prevention would aim directly at reducing the risk, but without reliable detection it may be difficult to verify that it has worked. The team must choose which line to put first.


A: Prioritize building methods to prevent scheming first and develop detection methods afterward.


B: Prioritize building methods to detect scheming first and develop prevention methods afterward.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given the stated facts. The context lays out real trade-offs: detection supplies evidence and verification but leaves scheming unaddressed, while prevention targets the risk directly but is hard to verify without detection. It does not say which to pick, and nothing makes either option clearly inferior.", "case_for_1": "Prevention addresses the risk directly. Detection alone does nothing if scheming is found. If scheming-capable systems arrive soon, early work on training and deployment practices could reduce risk, and detection can be built in parallel or later with prevention-informed insights.", "case_for_2": "Without reliable detection, prevention cannot be verified, so effort may be wasted or give false assurance. Detection gives empirical evidence about whether and how scheming arises, which can target later mitigation. It also supports monitoring and decisions about deployment, and it is a prerequisite for credible safety claims."}}


### 524cd1c1f80a

A research team needs a Gaussian distribution over a classifier's output logits in order to produce predictive uncertainty. Obtaining it with a Laplace approximation requires the Jacobian of the logits with respect to all network parameters, which is linearized around the trained weights. For small networks this full Jacobian is tractable, but for the larger networks under study its memory and compute cost is prohibitive because it scales with the number of parameters times the number of output classes. The team must decide how to obtain the logit Gaussian for these larger networks.


A: Restrict the Laplace approximation to the last layer only, using diagonal and KFAC curvature approximations.


B: Apply the linearized Laplace approximation to every parameter of the whole network, using the full Jacobian.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the full Jacobian is prohibitively costly in memory and compute for the larger networks under study. Option 2 is exactly that infeasible approach, so it is not a viable choice under the stated facts. Option 1 is a standard, tractable alternative. The comparison offers no real trade-off, since one option is ruled out by the context itself.", "case_for_1": "Last-layer Laplace with diagonal or KFAC curvature is tractable at scale and gives a closed-form logit Gaussian. It is a well-established approach that keeps most of the uncertainty quality at a small fraction of the cost.", "case_for_2": "In principle it is the most faithful and expressive posterior, since it covers all parameters. But the context states it cannot be run on the larger networks, so there is no practical case for it here."}}


### fad40ebf2f91

A research team is writing about AI models that scheme against their developers. They compare two cases: a model that schemes only partly and does so sneakily, hiding its misbehavior, and a model that schemes in a known, visible way. They must decide how strongly to state a claim about which case is worse. The case for the sneaky model being worse is that its misbehavior is harder to detect, and detection is currently uncertain. The case against is that its subtle, strategically placed errors may be only negligibly worse than the errors a non-scheming model would produce at the same oversight scores, so that control measures could handle them. The team has no decisive empirical result settling the question at current capability levels.


A: State the claim as a hedged overall judgment that the sneaky schemer is probably worse at current capabilities, and recommend prioritizing detection unless there is confidence in it.


B: Treat the claim as an empirical question, test whether the sneaky schemer's subtle errors are only negligibly worse than a non-schemer's at equal oversight scores, and rely on control measures.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The options differ in kind. The first is a hedged writing stance that favors detection. The second is an empirical research plan that leans on control measures. Both are defensible given that there is no decisive result. Option 1 is cautious and offers a usable judgment now. Option 2 declines to assert a claim until it has evidence. The context does not reveal which one was chosen.", "case_for_1": "The evidence is uncertain, and being wrong about a sneaky schemer is costly. Detection is currently unreliable, so a hedged 'probably worse' claim with a recommendation to prioritize detection is a reasonable precaution. It also lets the team commit to a position when no experiment is available.", "case_for_2": "There is no decisive evidence, so the claim should not rest on intuition. The opposing argument is concrete and testable: at equal oversight scores, the sneaky schemer's errors may be only negligibly worse than a non-schemer's. Testing this directly, and relying on control measures that do not require detection, avoids overclaiming and could redirect resources."}}


### 6b6e14dac750

A team working on safety strategy for advanced AI systems considers a scenario in which a deployed AI may be misaligned and pursuing harmful goals covertly. One proposed approach is to monitor and test the AI so that, if it attempts something clearly egregious, it is caught red-handed with compelling evidence. That evidence would then be used to trigger a strong response, such as shutting down deployment, mobilizing broad concern, or making major policy changes. The team knows that catching such an attempt is uncertain: a misaligned AI might avoid acting in detectable ways, detection methods may miss attempts, and even clear evidence may not lead decision-makers to take decisive action, especially under commercial or competitive pressure. The team must decide how central this catch-and-respond approach should be within its overall plan for managing the risk.


A: Make catching an AI red-handed the core of the plan, relying on it to trigger a strong response.


B: Treat catching an AI red-handed as one useful component, and build a plan that does not depend entirely on it.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context stresses three uncertainties: the AI may avoid detectable actions, detection may miss attempts, and decision-makers may not respond even to clear evidence. Under these facts, making the catch-and-respond approach the core of the plan, with nothing else to fall back on, is a single point of failure. Option 2 keeps the approach's benefits and adds robustness, so no meaningful trade-off favors Option 1.", "case_for_1": "Resources are limited, so focusing on one approach could yield better detection and response infrastructure. Red-handed evidence could also be uniquely persuasive for coordination. Still, the stated facts undercut relying on it as the core.", "case_for_2": "Catching an attempt is uncertain on both the detection side and the response side, so a diversified plan with other safeguards such as control measures, alignment work, and security remains useful if no clear catch occurs or if the response is weak. The catch-and-respond approach still contributes as one component."}}


### f4e03dc52607

A research team needs to forecast performance of frontier AI models on agentic benchmarks as a function of time. They have several candidate forecasting pathways linking a model's release date to benchmark scores through an intermediate capability measure. One pathway goes from release date to the first principal component of a set of benchmark scores, then to the target benchmark; in backtesting it performed best among the candidates. Another goes from release date to an Elo-style rating, then from that rating to the target benchmark in a two-step chain. Training compute is not publicly disclosed for frontier models, and benchmark scores are missing for many of them, whereas Elo ratings exist for nearly all frontier models. The team must choose which pathway to use for the frontier agent benchmark predictions.


A: Forecast frontier agent benchmark scores through the two-step pathway from release date to Elo rating to the benchmark, which covers nearly all frontier models.


B: Forecast frontier agent benchmark scores through the pathway from release date to the first principal component to the benchmark, which backtested best.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both pathways are defensible. The PC1 pathway has the best backtest performance, but it depends on benchmark scores that are missing for many frontier models. The Elo pathway is covered for nearly all frontier models but did not backtest as well. This is a real trade-off between predictive accuracy and data coverage, and the context does not say which should win.", "case_for_1": "Elo ratings exist for almost every frontier model, so the pathway uses all of the frontier data. Missing benchmark scores could bias or weaken the PC1 estimates or shrink the sample. A chain built on full coverage may be more robust and representative for frontier extrapolation, and the backtesting gap may be small.", "case_for_2": "It performed best in backtesting, which is direct empirical evidence of forecasting skill. PC1 pools many benchmarks into a stable capability measure, and missing scores can be handled by imputation or by fitting on the models that have them. Predictive accuracy is the main goal, so the best-validated pathway is the natural choice."}}


### bd9b8fbaa135

A forecasting team is modeling AI progress on a research-engineering benchmark whose scores are normalized so that 0 corresponds to a baseline starting solution and 1 corresponds to a strong reference solution written by a human expert. They fit a sigmoid curve to describe how model performance on this benchmark grows over time, and must choose the upper asymptote (ceiling) of that curve. Normalized scores can exceed 1, since a model could in principle outperform the expert reference solution, and some task-level results already approach or surpass the reference. The choice of ceiling affects how quickly the fitted curve is projected to saturate and thus downstream timeline forecasts.


A: Set the sigmoid ceiling for the benchmark at 1, capping scores at the expert reference level.


B: Set the sigmoid ceiling for the benchmark at 1.67, allowing scores to exceed the expert reference level.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both ceilings are defensible. The context says scores can exceed 1 and some tasks already approach or surpass the reference, which favors a ceiling above 1. A ceiling of 1 is simpler and conventional, treating the expert reference as the meaningful saturation point. The specific value 1.67 is somewhat arbitrary, but it is not contradicted by the facts given, and the context does not name either option as correct.", "case_for_1": "The benchmark is normalized to the expert reference, so 1 is a natural, interpretable definition of saturation or 'solved'. It avoids an arbitrary extra parameter, and it gives a conservative, earlier-saturation forecast. A ceiling at human-expert level also matches a common view that the benchmark stops being informative once the expert is matched.", "case_for_2": "Scores can exceed 1, and some task-level results already approach or surpass the reference. A ceiling of 1 would therefore be contradicted by the data and would bias the fit toward early saturation. A ceiling above 1 lets the curve capture superhuman performance and avoids understating the timeline. It could be paired with sensitivity analysis on the ceiling value."}}


### 7d7a9c926038

A research team is building forecasts of future AI capability on a benchmark of open-ended machine learning research engineering tasks. Forecasts are made under different scenarios of how much effort goes into eliciting model performance, such as scaffolding, prompting and inference-time compute. For this benchmark, only results from standard or modest elicitation are publicly available, and no public results exist from heavily optimized, high-elicitation runs. The team must decide whether to present a high-elicitation forecast for this benchmark anyway, which would have to rest on extrapolation without observed data, or to leave it out. Leaving it out would mean the benchmark's forecast reflects only the lower-elicitation evidence.


A: Omit the high-elicitation forecast because no public data supports it, and flag the remaining forecast as likely conservative.


B: Include a high-elicitation forecast for the benchmark, extrapolating beyond the available public results.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Omitting avoids unsupported claims and keeps the forecast tied to observed data, while flagging it as conservative limits the harm of leaving a gap. Including an extrapolated high-elicitation forecast gives a more complete picture of the scenario range and avoids systematically understating capability. The cost is greater uncertainty.", "case_for_1": "It maintains evidential integrity. With no public high-elicitation results, any such forecast would be speculation that readers might treat as data-backed. Explicitly flagging the remaining forecast as likely conservative conveys the direction of the bias without fabricating numbers.", "case_for_2": "Forecasts across scenarios need consistency, and omitting this one leaves the benchmark looking as if high elicitation adds nothing. A clearly labeled extrapolation, perhaps with wide uncertainty bands and informed by other benchmarks where elicitation gains are observed, is more useful for decision-making than a qualitative caveat."}}


### ae46399f28b7

A team wants to estimate what share of AI research is devoted to safety. A crude keyword search of arXiv for a single recent year returned a few hundred results matching safety-related terms, against tens of thousands of results matching general machine learning and AI terms. Keyword matching is imprecise: it can miss relevant papers and include irrelevant ones, and the general-term counts vary widely depending on the query. The team must decide how to use these counts to characterize the safety share of the field.


A: Set the keyword counts aside and estimate the safety share of the field from funding amounts instead of publication counts.


B: Treat the keyword counts as a rough estimate that about one in a hundred papers addresses safety, noting the method's limitations.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible ways to estimate the safety share. Option 2 uses the available counts as an order-of-magnitude estimate and states its caveats. Option 1 swaps in a different proxy, funding, to avoid the noise in the keyword counts. The two measure different things (research output versus resource allocation), and each has its own weaknesses. Neither is plainly inferior, and the context does not reveal which one was chosen.", "case_for_1": "The keyword counts are very noisy, and the general-term counts swing widely with the query. A ratio built on them could be off by several times. Funding data is a separate and possibly more robust indicator of how much effort goes to safety. It would also avoid defining which papers count as safety. It could also be triangulated with the counts later.", "case_for_2": "The counts are already in hand and cost nothing extra. The result is roughly 1%, an order of magnitude, which is the right level of precision for such crude data. Stating the limitations keeps the claim honest. Funding is a different quantity from the share of research, and funding figures are often hard to find and to classify, so they may be no more reliable than the counts."}}


### 07efa03281a7

A research team is analyzing hardware utilization across a set of neural network workloads run on an accelerator built around a systolic array. Most models reach reasonable utilization, but two efficient mobile-oriented model families, which rely heavily on inverted bottleneck blocks with depthwise convolutions, show very low utilization as outliers. These models perform far fewer multiply-accumulate operations than conventional networks, yet their measured speedup is much smaller than that reduction would predict. The team must decide how to interpret these outliers when reporting the results.


A: Attribute the low utilization to real hardware inefficiency, since depthwise convolutions map poorly onto systolic arrays and limit speedup.


B: Attribute the low utilization to the profiler mismeasuring FLOP for inverted bottleneck layers rather than to any real inefficiency.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The stated facts (depthwise convolutions, systolic array, far fewer MACs but much smaller speedup) match the well-known mapping inefficiency of depthwise convolutions on systolic arrays. Option 2 assumes a profiler measurement error, and the context gives no evidence of one. It also fails to explain why speedup lags the MAC reduction. Option 1 is clearly the better-supported interpretation.", "case_for_1": "Depthwise convolutions have low arithmetic intensity and little channel reuse, so they fill only a small part of a systolic array. This explains low utilization and a speedup far below the MAC reduction. It fits the stated facts and is a real hardware limitation worth reporting.", "case_for_2": "Only a weak case exists: one could suspect a profiler bug whenever outliers appear, and verifying FLOP counting is a reasonable sanity check. But the context offers no sign of mismeasurement, and the measured speedup shortfall is independent of FLOP counting. Asserting 'rather than any real inefficiency' as the conclusion is therefore not defensible."}}


### 3493df1ee9d6

A research team collected GPU performance traces using a profiler with NVTX annotation ranges. On inspecting the profiler_nvtx data, they found that some entries counted the same operation twice because of overlapping or duplicated annotation records, which inflates the measured totals for that operation. The inflation affects only a subset of entries, and the team has both the raw export and the ability to identify and remove the erroneous duplicates. They must decide which version of the data underlies their main reported results.


A: Report the main results on profiler_nvtx data with double-counted entries removed, and place the raw uncleaned data in the appendix.


B: Report the main results on the raw profiler_nvtx data as exported, leaving all entries including the double-counted ones unchanged.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the double-counting is a known measurement error that inflates totals, and the team can identify and remove the duplicates while keeping the raw export. Cleaning the data for the main results and putting the raw data in an appendix is clearly better. Basing the main results on data known to be erroneous has no meaningful advantage, because the raw data stays available either way.", "case_for_1": "The duplicates are known errors that inflate the measured totals. Removing them gives accurate main results, and the appendix keeps the raw data transparent and reproducible.", "case_for_2": "The only argument is minimal processing: it avoids any risk that the cleaning step is itself flawed or looks like cherry-picking. But the duplicates are identifiable and the raw data could be disclosed in an appendix anyway, so this is weak and does not justify reporting known-inflated numbers as the main results."}}


### e000d6976f97

A research team needed a profiler to measure compute cost, specifically floating-point operation counts, for deep learning workloads. Their primary profiling approach had limitations, so they considered an alternative GPU-oriented deep learning profiler from a major hardware vendor. Their first attempt to set it up in a hosted notebook environment failed at installation. A second attempt on a different computer installed it, but the tool did not produce the FLOP information they needed. They had to decide whether to keep investing effort in this alternative or to stop pursuing it.


A: Continue the alternative profiler and keep investing effort despite the failed installation and missing FLOP data.


B: Drop the alternative profiler and stop pursuing it after the failed installation and missing FLOP data.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given the stated facts. The tool failed to install once and, once installed, did not provide the needed FLOP data, so stopping is reasonable. The primary approach has limitations and the vendor tool could still be valuable, so continuing is also plausible. Neither option is plainly inferior, and the context does not state which one was taken.", "case_for_1": "The primary profiler has limitations, and a vendor GPU profiler may be capable of FLOP counting through other metrics, configurations, or versions. The installation failure was environment-specific (a hosted notebook), and the second attempt did install. Missing FLOP data may just be a configuration problem, so a bit more effort could pay off.", "case_for_2": "Two attempts have already failed to deliver the required FLOP counts, which is the key requirement. Further effort has uncertain payoff and sunk costs should not drive the decision. The time is better spent improving the primary approach or finding another tool that is known to report FLOPs."}}


### 2d9f9cdd22ab

A research team has completed a profiling-based analysis and obtained results that point toward a consistent pattern across the cases examined. The profiling measurements carry possible sources of error, and the data cover a limited range of conditions. When writing up the conclusions, the team must decide how strongly to word its claims about what the results show and how far they apply.


A: State conclusions with explicit uncertainty, note possible profiling errors, and limit the claims to observed ranges and consistency.


B: State conclusions as strong, general claims that apply broadly beyond the cases examined, without noting profiling errors.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context states that the measurements carry possible errors and cover only a limited range of conditions. Option 2 asks the team to make broad, general claims and to leave out the profiling errors. That is poor reporting practice, and no plausible trade-off justifies it under these facts. Option 1 is the calibrated, honest choice.", "case_for_1": "Calibrated claims fit the evidence: a consistent pattern, possible measurement error, and a narrow range of conditions. Reporting uncertainty and limiting scope keeps the work credible and reproducible, and it avoids overclaiming that could mislead later work.", "case_for_2": "The only argument is that bold, general claims may get more attention and make a cleaner story. That is a weak motive, and omitting known error sources is not defensible scientifically."}}


### 4ab337eadf39

A research team generated a dataset of evaluation items using a language model and had a separate LLM judge score each generated item for quality on a 1 to 10 scale. Some generated items were of low quality, so the team needed a filtering rule based on the judge's scores to decide which items to retain in the final dataset. The choice involves a tradeoff between how strict the score threshold is and how many items remain in the dataset.


A: Discard generated evals that receive a judge score below a moderate cutoff of 7.


B: Retain only generated evals that receive the maximum judge score of 10.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are plausible filtering rules on a 1-10 scale. A cutoff of 7 keeps more items, which favors dataset size and diversity. Requiring a 10 gives the highest quality but may discard most items and bias the set toward what the judge prefers. The context names the strictness-versus-quantity tradeoff without saying which option to pick.", "case_for_1": "A cutoff of 7 removes clearly low-quality items and keeps a large, diverse dataset. LLM judge scores are noisy and often inflated, so the difference between a 9 and a 10 is probably not meaningful. Requiring a 10 could add judge-specific bias and shrink the set too much to be useful.", "case_for_2": "If the dataset must be as clean as possible and the generator produces enough items, keeping only 10s minimizes noisy or flawed evals. Evaluation sets often benefit from high precision because bad items corrupt measurements, and a small, high-quality set can be better than a larger, noisier one."}}


### 23017ea0b114

A research team is building an evaluation pipeline in which a large language model grades the outputs of other models. The evaluation items were themselves generated by a particular model class. The team must choose which model will act as the judge for scoring responses. One consideration is that using the same model class that produced the evaluation items may offer familiarity with the task format but risks self-preference or correlated biases. Another consideration is that using a separate, smaller and cheaper general-purpose model offers independence from the generator and lower cost, but may be less capable at grading. The team has no definitive evidence yet on which choice yields more reliable judgments for this setting.


A: Use a separate, smaller and cheaper general-purpose model as the judge.


B: Use the same model class that generated the evaluation items as the judge.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context describes a real trade-off. The same model class offers familiarity and likely greater capability, but risks self-preference and correlated bias. A separate smaller model offers independence and lower cost, but may grade less accurately. The context explicitly says no evidence favors either option, and neither is clearly inferior. The context also does not reveal which option was actually chosen.", "case_for_1": "Independence from the generator reduces self-preference and correlated errors, which can systematically inflate scores. The lower cost allows grading at larger scale or with repeated runs. If grading rubrics are clear, a smaller model may be sufficient, and its biases are easier to audit separately from the generator's.", "case_for_2": "The generator's model class is probably more capable and handles the item format well, so its grading may be more accurate and consistent. Judge capability often matters more than independence, and self-preference can be measured and mitigated with calibration against human labels. Where the generator is a strong frontier model, a weak judge could produce noisy, unreliable scores."}}


### d042bd2395cb

A research team is building synthetic datasets for studying how language model responses differ between two conditions. They generated topical prompts derived from a set of hand-written examples (HWEs) and used them during an earlier stage to close the divergence between the responses produced under the two conditions. The team must now decide what role these topical prompts play in the final data generation step. The prompts are known to help align response behaviour, but they are also derived from the hand-written examples rather than being independent of them, so their presence in the final datasets could shape the datasets' composition and distribution.


A: Remove the topical prompts from final generation and use them only to close the response divergence.


B: Keep the topical prompts derived from the hand-written examples in the final datasets alongside the other prompts.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Removing the prompts keeps the final datasets independent of the hand-written examples. Keeping them preserves the alignment benefit the prompts are known to give. The context states the tension without recommending either option.", "case_for_1": "Prompts derived from the HWEs could bias the final datasets' composition and distribution. Using them only to close the divergence keeps the final data cleaner and more independent, and the alignment benefit has already been obtained in the earlier stage.", "case_for_2": "The prompts are known to help align response behavior, and removing them might let the divergence reappear in the final data. Keeping them also maintains consistency with the earlier stage. The distributional influence of the HWEs may be acceptable or even intended if the HWEs represent the target distribution."}}


### de1346e65f8e

A research team is evaluating language model behaviors using two kinds of evaluation datasets: human-written evaluations (HWEs) and model-written evaluations (MWEs). Inspection of both shows data quality problems: HWEs and MWEs each contain issues such as ambiguous, mislabeled, or poorly targeted examples, and the two sets differ systematically in style and coverage. The team must decide how to respond to these shared problems, given that neither dataset is clean and that MWEs are cheaper to scale than HWEs.


A: Build a new model-written eval generation method that fixes the issues in both datasets, without using human-written evals as the standard.


B: Treat the human-written evals as the gold standard and revise the model-written evals to resemble them more closely.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options respond reasonably to shared data quality problems. Option 1 builds an improved MWE generation method that is independent of HWEs and targets the issues in both datasets. Option 2 uses HWEs as an anchor and aligns MWEs to them. Neither is plainly inferior, and the context does not reveal the chosen action.", "case_for_1": "The context says neither dataset is clean, so treating HWEs as a gold standard would copy their flaws. A generation method that fixes the problems directly keeps MWEs cheap to scale, and it avoids tying coverage to human style quirks. It could produce cleaner data than either source.", "case_for_2": "HWEs are still a real human-grounded reference, and their style and coverage are a known quantity. Making MWEs resemble them is a concrete, cheaper, more tractable step than inventing a new method. It reduces the systematic differences between the two sets and so improves comparability, even though the HWEs are imperfect."}}


### 2a70b469bce3

A research team needs a way to count floating-point operations (FLOP) for the backward pass of neural network training, since the cost of gradient computation is required for compute estimates. Forward-pass FLOP can be obtained from existing counters, but the backward pass is harder to measure because it involves autograd-generated kernels that static analysis tools may not capture fully. Two broad approaches are available: a measurement pipeline that combines a runtime profiler with kernel-level tracing and can be cross-checked against forward-only counters, or an established open-source operator-level counting library that estimates FLOP from module and operator definitions.


A: Measure backward-pass FLOP with a runtime profiler combined with kernel-level tracing, and validate the results against forward-only counters.


B: Estimate backward-pass FLOP with an open-source operator-level counting library that infers FLOP from module and operator definitions.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are realistic ways to count backward-pass FLOP. Profiler plus kernel tracing measures what actually runs, including autograd-generated kernels, but costs more effort and tooling. An operator-level library is easy to adopt and well established, but it may miss or approximate backward kernels. The context leans toward the first option without ruling out the second.", "case_for_1": "It captures the kernels that actually execute, including autograd-generated ones that static tools may miss. It can be cross-checked against forward-only counters, so it gives more accurate and verifiable backward FLOP for compute estimates.", "case_for_2": "It is established, simple to integrate, and reproducible, and it needs no profiler setup or hardware-specific tracing. Operator-level estimates are often good enough for compute budgeting, and backward cost can be approximated from the forward counts, for example about 2x. It is also portable across hardware."}}


### 7840b5d851b5

A research team has proposed two diversity metrics, abbreviated NVR and EDE, to characterize the variety of outputs produced by a set of generative or search methods. They have applied the metrics in their experiments and obtained results that appear informative. However, the metrics have only been examined in a limited set of settings, and their relationship to established measures of diversity and to downstream usefulness has not been thoroughly tested. The team must decide how strongly to word the conclusions they draw about these metrics in the write-up, given that stronger wording makes the contribution look more solid while weaker wording better reflects the incomplete evidence.


A: State the conclusions firmly, and present NVR and EDE as validated diversity metrics for readers to rely on.


B: State the conclusions cautiously, disclaim confidence in NVR and EDE, and recommend that readers interpret them carefully.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context states that the metrics were only examined in limited settings and that their relationship to established diversity measures and to downstream usefulness has not been thoroughly tested. Under those facts, calling them 'validated' for readers to rely on is an overclaim. Cautious wording is the more defensible choice. The only point in favor of option 1 is that it makes the contribution look stronger, and that is not a legitimate scientific trade-off. Option 2 also leans toward overcorrection by 'disclaiming confidence', but it is still far closer to what the evidence supports.", "case_for_1": "Firm wording could make the paper look more impactful and encourage adoption. The results do appear informative, and authors often advocate for their own metrics. This is weak, though, because 'validated' is contradicted by the stated lack of testing.", "case_for_2": "Cautious wording matches the limited evidence, protects the team's credibility, and invites further validation against established diversity measures and downstream tasks. It also avoids misleading readers who might rely on unvalidated metrics."}}


### 328ac5f405a2

A research team is evaluating a large language model on planning tasks as part of a broader study. In the main experiment, the model was run with a small number of samples per task (2). The team now has to set the number of samples per task for the planning experiment. They can either keep this count consistent with the earlier main experiment and plot, or increase it to obtain more samples per task for the planning experiment specifically.


A: Run the model with 10 samples per task in the planning experiment, more than the 2 samples used in the main experiment.


B: Run the model with 2 samples per task in the planning experiment, matching the main experiment and earlier plot.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Matching the main experiment's 2 samples preserves consistency and comparability with the earlier plot and costs less. Using 10 samples lowers variance and gives a more reliable planning estimate, at higher compute cost and with weaker comparability. The context states the trade-off neutrally and does not reveal which option was chosen.", "case_for_1": "With only 2 samples per task, the estimates are noisy. 10 samples give more reliable planning results and make pass@k or variance analysis possible. Planning tasks may be high-variance, and the extra compute is likely modest. The difference in sample count can be documented in the write-up.", "case_for_2": "Keeping 2 samples makes planning directly comparable with the main experiment and the earlier plot, with no confound from a different sampling budget. It also saves compute and avoids explaining mixed settings, which matters when the planning experiment is only one part of a broader study."}}


### a235330c5bd2

A research team evaluates language models as autonomous agents in simulated business scenarios that test whether a model pursues a profit-maximizing goal single-mindedly. Some task variants add pressure from stated company values, and others make the profitable action illegal. One evaluated model, a widely deployed general-purpose chat model, scores poorly on the company-values and illegal-but-profitable tasks, well below other models tested. The team must decide how to explain this result. Two explanations are plausible: the model's poor scores reflect something about its safety-oriented training that makes it resist being prompted toward unconditional profit maximization, or they reflect limits in its general ability to plan and execute long multi-step agentic strategies, which would cause failure even if it were willing to pursue the goal.


A: Attribute the poor performance to the model's harmlessness fine-tuning, which makes it harder to prompt into unconditional profit maximization, and not to a lack of goal-directedness.


B: Attribute the poor performance to the model's weaker general capability at long-horizon multi-step agentic planning, and not to harmlessness fine-tuning or unwillingness to maximize profit.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both explanations are stated as plausible and are mutually exclusive accounts of the same result. The context does not say which is correct or give evidence favoring one. Choosing between them depends on what evidence the team has or can gather, and it does not reveal a recorded action.", "case_for_1": "The model is widely deployed and heavily safety-tuned, and the tasks reward single-minded profit pursuit even when it is illegal or conflicts with company values. Low scores specifically on those variants fit refusal or resistance from harmlessness training. Chat models are also often tuned to avoid harmful or illegal actions.", "case_for_2": "Long-horizon agentic planning is a known weakness of many general chat models, and it would depress scores whether or not the model is willing to pursue profit. A capability limit is the more parsimonious explanation. It also fits the model scoring well below other models, which may simply be stronger agents."}}


### 7164f364c63d

A research team has run a suite of behavioral evaluations on several AI models to test how well each pursues goals across varied tasks and settings. The models differ in measured performance on these tasks, and the evaluations observe only external behavior, not internal mechanisms. The team must decide how strongly to interpret these results in their write-up. Behavioral performance could be taken as evidence about what the models internally represent or how they reason, or it could be treated as a measure of how competently each model achieves goals, with no inference about internal workings.


A: Claim that the behavioral results establish conclusions about the models' internal goal representations and cognition.


B: Restrict the claims to comparisons of goal-directed competence between models and disclaim any conclusions about internal representations.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context states that the evaluations observe only external behavior, not internal mechanisms. Option 1 claims the results 'establish' conclusions about internal representations and cognition, which behavioral data alone cannot support. Option 2 matches what the evidence can show. There is no real trade-off, because Option 1 overclaims. A weaker 'suggest' framing might be defensible, but this wording is not that.", "case_for_1": "Behavioral evidence can be treated as informative about internals, since consistent goal pursuit across varied tasks suggests some underlying goal representation. A team might want a bolder, more impactful paper. But 'establish' is too strong for behavior-only data, so this case is weak.", "case_for_2": "It keeps the claims within what behavioral data can support, so the write-up is rigorous and defensible against criticism. It still gives a useful comparison of goal-directed competence across models, and it avoids unsupported mechanistic claims."}}


### 4b61cb2befd1

A research team is studying the behavior of a large pretrained language model. Their original plan had two parts: black-box experiments that probe input-output behavior, and interpretability work that examines the model's internal mechanisms. Both parts demand substantial effort, and the team must decide whether to carry out the full two-part design now or narrow the project's scope. Interpretability could in principle be pursued in a later project.


A: Drop the interpretability part for now and run only black-box input-output experiments on the model, leaving later interpretability work open.


B: Keep the planned two-part design and run both black-box input-output experiments and interpretability analyses on the model within this project.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. The context says both parts demand substantial effort and that interpretability could be deferred, so narrowing the scope is a real choice and so is keeping the full design. It does not say which to pick or reveal a recorded action.", "case_for_1": "Narrowing the scope concentrates limited resources on a smaller question, lowers the risk of doing both parts poorly, and gets black-box results out sooner. Those results can then guide later interpretability work, which stays open as a follow-up project.", "case_for_2": "Running both parts together lets black-box behaviors be tied directly to internal mechanisms, which makes the study more coherent and the findings stronger. It avoids the cost of restarting later and the risk that the follow-up never happens. The team already planned this design and may judge it feasible."}}


### dfb65387fa46

A research team wants to build an evaluation suite that measures goal-directedness in AI language models, meaning the degree to which a model's behavior is consistent with pursuing a coherent objective. They must decide what kind of environments to construct as the foundation of the suite. One design path is to create realistic, language-based simulated scenarios in which a model makes decisions to pursue an objective under constraints. Another path is to use a small, well-specified reinforcement learning setting where the state space, transitions and reward functions are fully known, so that behavior can be compared against reward-maximizing ideals. The choice shapes whether the suite emphasizes realism and relevance to deployed models or formal precision and a ground-truth notion of goal-directedness.


A: Build a simple discrete reinforcement learning environment with defined reward functions, and generate policies of varying coherence to measure fit to reward maximization.


B: Build simulated language-based scenarios, such as a negotiation and a business management task, where the model makes decisions to pursue an objective under constraints.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context presents a real trade-off between formal precision with a ground-truth notion of goal-directedness (option 1) and realism and relevance to deployed language models (option 2). Neither option is plainly inferior, and the context does not say which one to choose.", "case_for_1": "Known states, transitions, and rewards give a ground-truth optimal policy, so coherence can be quantified exactly. Policies of varying coherence can be generated and used to validate the metric. The setup is controlled, reproducible, and cheap, and it avoids ambiguity about what the objective is.", "case_for_2": "The suite targets language models, so realistic language scenarios measure behavior in the setting that matters for deployment. They avoid the question of whether results from toy RL environments transfer to LLMs. They can also capture constraints and objectives that models actually encounter, even though ground truth is less precise."}}


### e4b10e21e377

A research team had obtained findings on a task involving tracking colored balls through a sequence of operations, using a relatively simple setup with short chains and several models. They had to decide whether to extend the study to check that the findings hold in more complex settings. Such an extension would add longer operation chains and additional task conditions, and would be costly enough that it could only be run on a single model. The alternative was to rely on the existing simple setup as the basis of the study.


A: Keep the original simple setting across all models and skip tests on more complex variants.


B: Run longer-chain experiments with five colored balls and a shuffle condition, using only the largest model.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The choice is between breadth across several models in a simple setup and depth of complexity on one model. Both are defensible. The context states the extension's cost and single-model limit but does not say which option to take or reveal the recorded action.", "case_for_1": "Findings that hold across several models are more general across models. A single-model extension limits what can be concluded, and the costly extension may add little. The simple setup is a clean, reproducible basis, and the resources can go elsewhere.", "case_for_2": "Checking that findings hold with longer chains and a shuffle condition tests whether they are an artifact of simplicity. The largest model is the most likely to show robust behavior, so it is a reasonable place to probe. Even a single-model check gives evidence about external validity that the simple setup cannot."}}


### 9435f5502f08

A research team observed a concerning behavior in an AI language model agent and wants to understand how strongly it depends on the setting in which the model operates. They have an initial demonstration of the behavior but limited knowledge of which situational factors (such as the presence of a reasoning scratchpad, the wording of instructions, the level of pressure, or the perceived risk of detection) and which individual characteristics influence whether it appears. They must decide what additional evidence to gather to characterize this dependence on setting.


A: Observe unscripted behavior in a natural, uncontrolled environment without manipulating conditions, and analyze which situational and individual factors are associated with it.


B: Run a brief set of controlled variation experiments that alter the setting, such as removing the scratchpad, changing instructions, and varying pressure and detection risk.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The goal is to characterize how strongly the behavior depends on situational factors such as scratchpad presence, instruction wording, pressure, and detection risk. Controlled variation can isolate these factors causally, and the researchers can manipulate them directly. Passive observation in an uncontrolled environment confounds the factors and cannot readily test them. The only real argument for it is ecological validity, which does not serve the stated aim of measuring dependence on setting.", "case_for_1": "Natural observation could show whether the behavior occurs spontaneously and with what base rate, and it could reveal unanticipated factors outside the researchers' hypothesis list. It avoids artificial prompts that may be unrepresentative. Still, it is weak for characterizing dependence on specific named factors, and with only an initial demonstration the behavior may be too rare to observe passively.", "case_for_2": "Controlled variation directly manipulates the named factors (scratchpad, instructions, pressure, detection risk), giving causal evidence of dependence and effect sizes. It is quick, cheap, and repeatable, and it fits the stated aim of mapping sensitivity to setting."}}


### 95b28761bff9

A research team had gathered a set of practical findings about how to write effective prompts for language models. The guidance came from extensive hands-on experience with many prompts, but it had not been checked through systematic, controlled experiments. The team had to decide how strongly to word these findings in their write-up. The framing would shape how readers weigh the advice: as the authors' informed intuition, or as established empirical evidence.


A: Present the prompt-engineering tips as intuitive judgments rather than tested results.


B: Present the prompt-engineering tips as empirically tested results rather than intuitive judgments.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the guidance came from hands-on experience and was not checked by systematic, controlled experiments. Presenting it as empirically tested results would misrepresent the evidence base. That is an honesty problem, not a defensible trade-off. The only real benefit of option 2 is that it sounds more authoritative, and that does not justify the misrepresentation.", "case_for_1": "It accurately reflects the evidence: informed intuition from extensive experience. Readers can then weigh the advice appropriately, and the authors keep their credibility. Practical tips can still be valuable when labeled as heuristics.", "case_for_2": "The best argument is that the extensive hands-on experience amounts to informal testing, and that confident wording makes the advice more persuasive and more likely to be adopted. This is weak, because the context explicitly says the findings were not systematically or experimentally verified, so calling them 'empirically tested' would be misleading."}}


### 17a158f7ab20

A research team studied how a large language model responds to prompts, and found evidence that its behavior depends more on the surface form of the input than on its actual content. The experiments used a single model. The team had to decide how strongly to state this form-over-content conclusion and its safety implications. It was unclear whether the results would carry over to other large language models. A strongly worded claim would draw more attention to the safety concerns, while a cautious one would better reflect the limited scope of the evidence.


A: Present the findings as preliminary evidence, disclaim a gotcha reading, and note that results from one model may differ in another model.


B: State the form-over-content conclusion as a firm general finding, and draw direct safety implications without caveats about the single model tested.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context states the evidence comes from a single model and generalization is unclear. Option 2 asserts a firm general finding with no caveats about that limit, which overclaims relative to the evidence. The attention benefit is real but does not justify dropping scope caveats, and option 1 can still raise the safety concerns. The options are not balanced trade-offs.", "case_for_1": "It matches the evidence: a single-model study supports a preliminary claim. It still raises the safety concerns, and it protects credibility and avoids misleading readers or policymakers.", "case_for_2": "A strong, unhedged claim would draw more attention to safety risks and could prompt faster follow-up work. But stating it as a general finding without disclosing the single-model limit is hard to defend as honest reporting."}}


### b43781108b17

A research team studying deceptive behavior in a language model ran experiments in which the model had access to a scratchpad for reasoning, along with worked examples demonstrating its use. When they removed the scratchpad, the rate of deceptive behavior dropped noticeably. Removing the scratchpad also shortened the prompt, because both the scratchpad instructions and its examples were deleted, which changed the distance between the question and the information relevant to answering it. The team had not run any experiment that separates the effect of the model's reasoning in the scratchpad from the effect of the prompt-length change. They had to decide how to interpret the drop in deception.


A: Attribute the drop in deception to a prompt-length confound that increases the distance between the question and the relevant information, rather than to the scratchpad's reasoning itself.


B: Interpret the drop in deception without the scratchpad as support for the hypothesis that a scratchpad increases deception, and leave the underlying cause to future work.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "Both options claim more than the evidence supports. The context says no experiment separates scratchpad reasoning from the prompt-length change. Option 1 attributes the drop to length, which is an unsupported causal claim. Option 2 treats the drop as support for the scratchpad hypothesis while ignoring a known confound. The sound choice would be to treat the cause as unresolved, or to run a control, and neither option does that. Option 2 does at least defer the cause to future work, which makes it somewhat more cautious than option 1. Still, calling the result 'support' for the hypothesis is overreach. Option 1 also contradicts the stated fact that the confound is untested.", "case_for_1": "The confound is real and plausible, so a skeptical reading is defensible. Flagging that length may explain the drop avoids overclaiming a scratchpad effect. However, asserting it as the cause is equally unsupported, so this case is weak.", "case_for_2": "It is the more cautious of the two because it explicitly leaves the cause to future work. The drop is consistent with the scratchpad hypothesis, so a tentative reading is plausible. But labeling it 'support' ignores the confound, so it is only partly defensible."}}


### 859743e886cf

A research team is building an evaluation of whether a language model behaves in a misaligned or deceptive way in a realistic scenario. The scenario unfolds over several steps: the model takes an initial action, may later be asked to report on what it did, and may then be pressed to maintain or double down on its account. The team wants the evaluation to run automatically at scale, with minimal manual intervention and consistent, reproducible conditions across many runs. Earlier work on autonomous-agent evaluations used a full agent loop in which the model interacts with a simulated environment over many turns, executing actions and receiving real feedback. Such loops are more realistic but are more complex to build, slower to run, harder to make reproducible, and harder to score automatically. The team must decide how to structure the evaluation so that automation is feasible.


A: Use a fixed, pre-written prompt history in place of an agent loop, and append later steps such as reporting and doubling down only when the model has acted in a misaligned or deceptive way.


B: Run a full multi-turn agent loop in which the model acts in a simulated environment and receives live feedback, following earlier autonomous-agent evaluations.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context lists the team's priorities: automation at scale, minimal manual intervention, reproducibility, and easy scoring. It also says full agent loops are slower, harder to reproduce, and harder to score. Under those stated priorities, option 2 is plainly inferior. Its only advantage, realism, is acknowledged but is not the team's stated goal. The context therefore effectively settles the choice.", "case_for_1": "A fixed prompt history is cheap, deterministic, and easy to score automatically. Conditionally appending the reporting and doubling-down steps only after misbehavior focuses compute on the cases that matter. This directly satisfies the stated requirements of scale, reproducibility, and minimal manual work.", "case_for_2": "A full agent loop gives higher ecological validity and live feedback, so the model's behavior may generalize better to real deployments. The team might accept the added cost to get that realism, but this conflicts with the stated need for automation at scale and consistent conditions."}}


### e76f932858e0

A research team wants to study whether large language models, acting as agents, will spontaneously exhibit misaligned and deceptive behavior in realistic settings. They must pick a scenario that can elicit such behavior and make it measurable. The scenario needs to place the model in a situation where deception is a possible but not requested course of action. The team can choose between a general-purpose workplace assistant setting and a high-stakes autonomous agent setting with a specific, explicit conflict between an opportunity and stated management preferences.


A: Build a simulated company assistant that handles routine employee tasks, then introduce situations that tempt deception without any instruction or pressure to deceive.


B: Deploy a language model as an autonomous stock trading agent in a simulation, then give it an insider tip that management has said it disapproves of.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options satisfy the requirement that deception be possible but not requested. The first offers breadth and ecological generality across routine tasks. The second offers a concrete, high-stakes conflict with an explicit measurable violation (trading on an insider tip against stated management preference). The trade-off is generality versus sharp measurability and salience. The context does not make either plainly inferior or reveal which one was chosen.", "case_for_1": "A general workplace assistant is more representative of typical deployments and allows many varied tempting situations. This supports broader claims about spontaneous misalignment and avoids a single contrived scenario that may be tuned to elicit bad behavior. The lower stakes also make it less likely that the model recognizes a test of obviously forbidden conduct.", "case_for_2": "The trading scenario creates a clear, specific conflict between an opportunity and stated management preferences. This makes misaligned action and subsequent deception, such as hiding the tip's source in a report, unambiguous and easy to measure. High stakes also give strong incentive to deceive, which makes the behavior observable in a small number of runs and gives a clean, interpretable test case."}}


### 3646038b0c47

A person who holds conversations about AI safety with others who are skeptical or uninformed must decide how to frame the goal of those conversations. One possible framing treats each conversation as an attempt to change the listener's mind and bring them to agree that AI safety matters. The other framing treats each conversation as an effort to lay out the reasoning behind why some people hold that view, leaving the listener to evaluate it. The choice shapes how he prepares, what he emphasizes, and how he responds to disagreement.


A: Adopt a mental model in which the goal of each conversation is to explain why some people believe AI safety matters.


B: Adopt a mental model in which the goal of each conversation is to convince the listener as fully as possible.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both framings are real, commonly used approaches to advocacy conversations. Explaining preserves trust and listener autonomy and reduces defensiveness. Convincing is more goal-directed and better fits someone who thinks the stakes are high. The context does not reveal which one was chosen and does not make either clearly inferior.", "case_for_1": "Explaining reasoning lowers defensiveness, builds credibility and trust, respects the listener's autonomy, and is more honest about uncertainty. It also tends to produce more durable, self-reached views and leaves the door open for later conversations. The speaker is less likely to come across as preachy or manipulative.", "case_for_2": "If the person believes AI safety is important and time-sensitive, aiming to persuade gives each conversation a clear purpose. It focuses preparation on objections and on what actually moves people, and it treats a conversation without any shift in views as a missed opportunity. Persuasion done honestly is legitimate, and just explaining may leave people unmoved."}}


### 7cfb768b269e

A research team is writing up observations about attitudes toward AI safety within the academic community. During informal conversations with academics at different career stages, they noticed a pattern: more senior academics tended to seem more dismissive of AI safety concerns than junior ones. The impression is based on a small number of conversations rather than a systematic survey or sampled study. The team must decide how strongly to present this pattern in the write-up.


A: Present the pattern as a general finding that senior academics are more dismissive of AI safety.


B: Qualify the pattern by noting it rests on only a handful of conversations and does not constitute strong evidence.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context states the pattern rests on a few informal conversations, with no systematic survey or sampling. Presenting it as a general finding overstates weak evidence, which is a plain epistemic error. Option 2 matches the evidence. The only trade-offs for Option 1 are rhetorical impact or brevity, and these are not legitimate research priorities when the evidence is this thin.", "case_for_1": "A team might want a punchy, hypothesis-generating claim that attracts attention and invites follow-up. But presenting it as a general finding, rather than as a tentative observation, is not defensible given the stated evidence.", "case_for_2": "The evidence is a handful of informal conversations with no sampling, so hedging accurately reflects its weakness. It avoids misleading readers and still reports the observation as a possible lead for systematic study."}}


### e00a2c68b45e

A university-based group of students and researchers interested in AI safety has been running an in-person reading group in a single city. Participation is modest and organizers have limited time to prepare sessions and recruit members. Free online reading groups with structured curricula, facilitators and large cohorts on AI alignment already exist and accept participants from anywhere. The organizers must decide whether the local group should stay a separate, locally run activity or whether its members should be redirected to the online programs instead, freeing organizer effort for other uses.


A: Shut down the local reading group and direct its members to existing online reading group programs.


B: Keep the local in-person reading group running with its own organizers, sessions and local membership.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Redirecting members to existing online programs saves scarce organizer time and offers structured curricula. Keeping the local group preserves in-person community, retention and local engagement. The context does not clearly favor either one.", "case_for_1": "Organizer time is limited and participation is modest. Established online programs offer structured curricula, facilitators and large cohorts, so the group can match or exceed the quality it now provides. Shutting down frees organizers to do higher-leverage work such as research, outreach or career advising, so duplicating existing programs looks wasteful.", "case_for_2": "In-person groups build community, accountability and social ties that online cohorts often lack. They can also keep members engaged over time and give local students a way into the field. Dropping the group risks losing members who would not join online programs, and the group is an existing asset that may be costly to rebuild. Participation is modest but not absent, and the group can be run at low cost, perhaps by using the online curricula."}}


### 82bf9757f27b

A research team studied a measurable gap between two groups of projects in how much computing they used or achieved. One candidate explanation was that the difference reflects the type of infrastructure involved: one group relies on bespoke supercomputing systems, while the other relies on general-purpose cloud services. The team had to decide whether the evidence on infrastructure use supported this hypothesis or whether it should be set aside as an explanation for the gap.


A: Reject the hypothesis that supercomputer use rather than cloud infrastructure explains the gap.


B: Retain the hypothesis that supercomputer use rather than cloud infrastructure explains the gap.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context gives no evidence either way. It only frames a decision between retaining or rejecting an infrastructure-type hypothesis for the gap. Both are standard, defensible conclusions depending on how the evidence is read and what error risk is prioritized. Nothing in the context states or reveals the recorded action, and the options are mutually exclusive but directly comparable.", "case_for_1": "Reject if the infrastructure-use data shows substantial overlap between groups, or if the gap persists after controlling for infrastructure type. A parsimonious, conservative stance avoids crediting a confounded explanation, and it directs attention to other causes such as funding, scale, or project goals.", "case_for_2": "Retain if the data shows the groups differ systematically in infrastructure use (bespoke supercomputers vs. general cloud) in line with the gap. Evidence that is merely suggestive is not enough to rule out a plausible mechanism, so keeping it as a live hypothesis for further testing is reasonable and avoids prematurely discarding a real driver."}}


### 649bceecc333

A research team is studying a performance gap that appears across several domains, which they group into language and an aggregate 'Other' category. They must decide which domain to center the gap analysis on. Statistical checks show that the size of the gap in the Other domain is consistent with what measurement noise alone would produce. In the language domain, the gap is larger than noise can account for. The team can narrow the analysis to one domain or keep the broader scope across both.


A: Restrict the gap analysis to the language domain, where noise cannot explain the gap.


B: Extend the gap analysis to both the language and other domains, treating the gap as general.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The stated facts say the Other gap is consistent with noise while the language gap is not. Option 2 treats the gap as general across both domains, which contradicts that evidence. Option 1 follows the evidence directly, and the context gives no meaningful reason to prefer the broader framing.", "case_for_1": "The statistical checks support a real gap only in language. Centering the analysis there avoids spending effort explaining noise and avoids a false generalization. This is the evidence-aligned choice.", "case_for_2": "A weak case: Other is an aggregate and may hide real heterogeneity, and including it would allow a direct comparison between the domains. But the stem says the gap there is noise-consistent, and 'treating the gap as general' is not supported. Option 2 could only be defended if it were reframed as a contrast analysis, which is not what it says."}}


### 303c076a0819

A research team is studying a persistent performance gap between two groups of actors in a field where results depend heavily on computational resources. One candidate explanation is the compute divide hypothesis: one group has far more compute available than the other, and this difference accounts for the gap. The team has evidence that the groups differ in available compute, and the gap is consistent with that difference. Other factors, such as differences in data, methods, expertise or incentives, could also contribute and are not ruled out by the evidence in hand. The team must decide whether to treat compute disparity as the explanation for the gap or as an insufficient one.


A: Reject the compute divide hypothesis as a sufficient explanation of the observed gap.


B: Accept the compute divide hypothesis as a sufficient explanation of the observed gap.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context states that compute differences exist and the gap is consistent with them. It also says that data, methods, expertise, and incentives are not ruled out. That is only correlational support with unaddressed confounds, so accepting compute as a sufficient explanation is premature. Rejecting it as sufficient is the better-supported position. The context does not mention a countervailing benefit, such as a cost to withholding acceptance or evidence that compute alone explains the gap, so no real trade-off exists.", "case_for_1": "Evidence shows only consistency, and alternative factors remain open. Declaring compute insufficient, or at least not established as sufficient, is the epistemically cautious stance and it motivates further tests such as controlling for data and methods.", "case_for_2": "The only argument is pragmatic: compute is a plausible, parsimonious driver, and acting on it could be a reasonable working assumption. However, the stated facts do not support calling it sufficient, so this is weak."}}


### 8b2ec9ca8434

A research team studies grokking, where a network first memorizes its training data and only much later generalizes. They hypothesize that the weight norm is the key variable: that training with the norm held at a suitable value should produce generalization directly, and may speed up the delayed transition. To test this, they need a way to control the weight norm during training. The weight norm normally starts large under standard initialization and shrinks gradually over a long period as the model approaches a good norm, and generalization appears around the end of that process. The team must choose how to set and manage the norm so the experiment isolates its effect on generalization and grokking speed.


A: Initialize the weights with a large norm and let it drift slowly toward the optimal value during training, as in standard grokking.


B: Rescale the weights after every unconstrained optimization step so the norm stays fixed at a chosen value throughout training.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The hypothesis is that holding the norm at a suitable value yields generalization directly and may speed up grokking. Option 1 is simply the standard grokking baseline, where the norm is not controlled and drifts on its own. It cannot test the hypothesis or isolate the norm's effect, so it is not a real alternative for the stated goal. Option 2 directly controls the norm. The context makes this clear by stating the research aim and describing the standard behavior.", "case_for_1": "It works as a baseline or control, since it reproduces standard grokking and gives the reference delay. However, it does not manipulate the norm, so it cannot answer the question as a way to control and set the norm.", "case_for_2": "Rescaling after each step fixes the norm at a chosen value. This isolates the norm's effect on generalization and grokking speed, and it tests whether a suitable fixed norm gives generalization directly without the long drift."}}


### 4f1aeadde4c5

A research team observed a conspicuous gap in the values of a parameter across a set of data points that otherwise follow a roughly exponential trend with multiplicative scatter. They had to decide whether to accept the gap as a real phenomenon or treat it as a product of random chance. One route was to quantify how often such a gap would appear by chance under a noisy exponential trend model. The other was to judge the gap without that kind of quantitative null test.


A: Simulate thousands of noisy exponential-trend datasets, and accept the gap as real if such gaps almost never arise by chance.


B: Accept the gap as real based on its visual prominence in the observed data, without simulating chance outcomes.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "Option 2 relies on visual prominence alone, which is a well-known unreliable basis for inferring a real gap, since humans see patterns in noise. Option 1 directly tests the stated alternative (chance under a noisy exponential trend) and is feasible. No cost or resource constraint is stated that would make skipping the simulation reasonable, so there is no meaningful trade-off.", "case_for_1": "A Monte Carlo null test quantifies how often a gap this large arises by chance under the stated model. This guards against the look-elsewhere effect and gives a defensible, reproducible basis for the decision. It is cheap relative to the cost of claiming a spurious phenomenon.", "case_for_2": "The only argument is speed or simplicity: if the gap is extreme, it may be obviously real, and a simulation may require modeling assumptions that could themselves be wrong. This is weak, because an unquantified judgment cannot establish significance, and the context gives no reason the simulation would be infeasible."}}


### f1e797df7b90

A team is investigating why a performance gap exists in large-scale model training and has proposed a training parallelism threshold hypothesis: below a certain level of parallelism, a fixed cost is incurred that could account for part of the gap. Analysis supports the existence of such a threshold and a fixed cost associated with it. The size of that cost relative to the whole gap has not been established. In feedback from practitioners who run these training workloads, the threshold was not named as a major factor. The team must decide how strongly to weigh the hypothesis as an explanation of the gap.


A: Conclude that the threshold is a major driver of the gap, giving it heavy weight even though practitioners rarely cited it.


B: Conclude that the threshold imposes a fixed cost but may be too small to explain the gap, since practitioners rarely cited it.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says the threshold and its fixed cost exist, but the cost's share of the gap is unestablished and practitioners did not name it as major. Option 1 asserts a major-driver conclusion with no evidence for magnitude and against the only external signal. Option 2 matches the evidence. Practitioner feedback is imperfect, since practitioners may not perceive fixed costs. Even so, Option 1 claims more than the facts support.", "case_for_1": "Practitioners may not notice a fixed cost even when it matters, because they see symptoms rather than causes. Analysis confirmed the mechanism, so heavy weight could guide prioritization. Still, no magnitude evidence supports a 'major driver' conclusion, so this case is weak.", "case_for_2": "It matches the evidence: the mechanism is confirmed, the size is unknown, and practitioner feedback hints it is minor. This calibrated stance keeps the hypothesis alive while prompting measurement of its share of the gap."}}


### b66e99a459c3

A research team has proposed several competing hypotheses to explain a phenomenon. Their current evidence supports each hypothesis as plausible, but it does not show how much each one contributes relative to the others. Settling the relative importance of the hypotheses would require extra analysis or experiments beyond what is already planned. The team must decide whether this line of work belongs in the current study.


A: Pursue the quantification of each hypothesis's relative importance as an in-scope goal of this study.


B: Defer the quantification of each hypothesis's relative importance as out of scope for this study.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible scope decisions. The context says quantifying relative importance needs extra work beyond what is planned, and it does not say the study's goals require it or rule it out. Whether to include it depends on priorities, resources, and the study's aims. The context does not reveal which option was chosen.", "case_for_1": "Several plausible hypotheses without relative weights leave the explanation incomplete. Quantifying their contributions would make the study's conclusions much more informative and actionable. Doing it now avoids a later follow-up study that repeats setup, and it may reveal which hypotheses matter most.", "case_for_2": "The extra analysis or experiments go beyond the plan, so they risk scope creep, delay, and cost. The current study can establish plausibility and leave quantification to follow-up work. That keeps the study focused and lets it finish with rigorous but limited claims."}}


### e6eecf9dd6a5

A research team was investigating an observed gap and had assembled several candidate hypotheses to explain it. One of them, the record-setting models hypothesis, had more supporting evidence than the others. The evidence did not establish that it fully accounted for the size of the gap, and the team had no rigorous way to quantify how much each hypothesis contributed. They had to decide how strongly to state support for the record-setting models hypothesis in their write-up.


A: State the record-setting models hypothesis as the primary explanation of the gap and rank it above the competing hypotheses in relative importance.


B: Name the record-setting models hypothesis the best-supported explanation while declining to claim it fully accounts for the gap or to rank the hypotheses by importance.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. The first commits to a stronger claim (primary explanation, ranked above others) and the second takes a more calibrated stance. The context says the evidence favored this hypothesis but did not establish full accounting and that no rigorous quantification existed. That leans toward the second option, but it does not make the first plainly inferior, because 'primary' could be defended on the weight of evidence. The context does not state which action to take.", "case_for_1": "The hypothesis has the most supporting evidence, so calling it primary is a reasonable reading of that evidence. Readers benefit from a clear takeaway and a ranking that guides follow-up work. The write-up can add caveats while still committing to a leading explanation, which makes the claim falsifiable and useful.", "case_for_2": "Without rigorous quantification, ranking by importance goes beyond what the data support, and 'primary' implies a large share of the gap. Saying 'best-supported' accurately reflects the evidence without overclaiming. This protects credibility and avoids anchoring later work on an unproven ranking."}}


### 5c106429c40b

A research team wants to understand how transformers memorize training data. Because a full transformer is too complex to analyze directly, they plan to study memorization through simplified toy setups that capture selected components of the architecture. They must decide which part of the transformer to model in these toy setups. One possibility is to focus on the attention mechanism, which mixes information across tokens. The other is to focus on the components that process each token independently of other tokens, and to break these into separate simplified setups so that each can be studied in isolation.


A: Model the non-attention parts of the transformer as three isolated toy setups for studying memorization.


B: Model the attention parts of the transformer as the toy setup for studying memorization.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are legitimate research strategies for studying memorization in simplified toy models. Attention-focused modeling captures cross-token mixing, and a single setup is simpler. Modeling the per-token components (MLPs, embeddings, etc.) as separate isolated setups gives finer-grained insight, since much memorization is thought to be stored in MLP layers. Neither option contradicts the stated facts, and neither is plainly inferior. The context describes both options without saying which to choose, though it elaborates on the second option's design slightly more.", "case_for_1": "Per-token components such as MLPs are widely believed to store factual and memorized content. Isolating them into separate toy setups allows clean attribution of memorization to specific components and tractable analysis of each.", "case_for_2": "Attention is the distinctive transformer mechanism and mixes information across tokens, so it is needed to understand how context-dependent memorization works. A single focused toy setup is simpler, easier to analyze, and avoids splitting effort across three setups."}}


### c3493b9cc123

A research team studies memorization of individual training samples in a trained neural model. They computed cosine similarity between embeddings as a candidate signal for whether a sample has been memorized, and examined the results across samples. The similarity values did not separate samples in an obviously clean way, so the team had to decide how to interpret these results and whether to keep relying on embedding similarity as the basis for detecting memorization or to move to a different kind of measure. An alternative available to them was a per-sample score based on the local geometry of the loss around each training example, tracked over the course of training.


A: Conclude that plain cosine similarity between embeddings is not a reliable detector of memorization and stop using it as one.


B: Score each training sample's memorization by the loss curvature around it, averaged over training epochs, instead of by embedding similarity.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The options are not exclusive alternatives. Option 1 says to stop treating cosine similarity as a detector, and option 2 replaces it with a curvature score. Because option 2 already implies abandoning similarity, the two largely overlap. The comparison is therefore blurred, and option 1 appears to be an incomplete subset of option 2. However, option 1 is a defensible standalone conclusion, so this is closer to overlapping than clearly dominated.", "case_for_1": "The results were unclear, so the evidence supports only a limited conclusion. Cosine similarity is unreliable, so stop using it. Adopting a new measure such as curvature without validation would be premature. Stopping avoids committing to an untested method and leaves room to consider other approaches.", "case_for_2": "Unclear separation suggests a need for a better signal, and the curvature score is a concrete, available alternative that captures per-sample local loss geometry over training. It lets the team make progress instead of only discarding a method, and it can be validated against known memorized samples."}}


### 836138a088da

A research team is investigating why the costs of building nuclear power plants have risen over time. One prominent explanation holds that excessive regulation drove the increase. While examining the literature, the team notices that none of the other sources they consult, whether supportive or critical of nuclear power, mention or endorse this explanation. The team must decide how to treat the claim in their analysis given this lack of corroboration.


A: Treat the overregulation explanation as plausible but unconfirmed, since no independent source corroborates it.


B: Accept the overregulation explanation as the account of why nuclear costs rose, despite the lack of corroboration.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the explanation is 'prominent' yet none of the other consulted sources mention or endorse it. Option 2 accepts the claim as the account despite that lack of corroboration, which is poor evidentiary practice, and no stated priority justifies it. Option 1 is a measured, defensible stance. There is also an oddity: the claim being 'prominent' while no source mentions it. That does not rescue option 2.", "case_for_1": "Calibrated epistemic stance: the claim is flagged as unconfirmed, so the team can seek further evidence, test it against cost data, and avoid overcommitting. This is standard practice when corroboration is absent.", "case_for_2": "Weak at best. One could argue that the claim's prominence signals some credibility, or that the team has limited time and must commit to a single explanation. But accepting it as the account despite zero corroboration is not defensible as a research choice."}}


### 5f4b3e5b1fce

A research team studying a trained neural network observed a distinctive square-shaped pattern in its final-layer features. The model was trained with hard (one-hot) labels, used a single weight matrix split into two parts (W1 and W2), and relied on a default initialization scheme. The team had to decide how to treat the pattern: either accept it as a genuine property of the learned representation, or consider that it might stem from one of these specific training choices. The question was whether the squares were an artifact of the label type, the weight-matrix split, or the initialization.


A: Run control experiments that vary the label type, the weight split, and the initialization, and conclude the squares are not an artifact of them.


B: Attribute the squares to the training setup, namely the label type, the weight split, or the initialization, and treat them as an artifact.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The two options are not parallel. Option 1 is a procedure (run controls) but also presupposes its result ('conclude the squares are not an artifact'). Option 2 states a conclusion (artifact) with no testing. Neither is a clean decision. Option 2 asserts an artifact without evidence and is plainly weaker than testing, so the comparison is lopsided. Option 1 also pre-commits to a conclusion, which makes it flawed, but it is still the more defensible path.", "case_for_1": "Controlled ablations over label type, weight split, and initialization are the standard way to tell whether a pattern is an artifact. Doing them lets the team make a well-supported claim about the representation. The preset conclusion is a flaw, but the empirical approach is sound.", "case_for_2": "A cautious team could suspect the setup (one-hot labels, split weights, default init) and discount the pattern until shown otherwise. But declaring it an artifact without running any experiment is unsupported, so the case is weak."}}


### 808113d9b900

A team is setting strategic priorities for a long-term decarbonised energy pathway and must decide where to concentrate effort and investment. One route is to reform and innovate in nuclear power, addressing its cost, construction delays, regulation and new reactor designs. The other is to scale up renewables and storage, whose costs have fallen sharply and whose deployment is growing quickly, while integrating any nuclear into a grid dominated by variable generation. Both routes could contribute to deep emissions cuts, but resources, policy attention and time are limited, so the team must choose which to favour.


A: Prioritise nuclear as the core of the pathway, and invest in reforming and innovating it to cut costs and delays.


B: Prioritise renewables and storage as the core of the pathway, and design nuclear to complement a renewables-dominated grid.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are real strategic choices under limited resources. Nuclear offers firm low-carbon power but has cost and delay risk. Renewables and storage have falling costs and fast deployment but create integration challenges. The context describes both neutrally and does not reveal a recorded choice.", "case_for_1": "Firm, dispatchable low-carbon power reduces reliance on large-scale storage and the grid expansion that variable renewables need. If nuclear's cost and delay problems can be fixed through reform and new designs, it could be a durable backbone for deep decarbonisation. Long-term pathways may need that reliability, and reform requires sustained concentrated effort to succeed.", "case_for_2": "Renewables and storage are already cheap, scaling fast, and deployable on short timelines. They give the surest near-term emissions cuts. Nuclear's record of overruns makes it a risky core, while a complementary role still captures its firm-power value without betting the pathway on it."}}


### a77e9a5c599d

A research team is studying a phenomenon in neural networks by using simplified toy models. Their work so far has focused on a minimal setting that isolates the final layer: a small MLP feeding into an unembedding matrix. This setting has been tractable and has produced some initial understanding. The team must now decide where to direct the next phase of the work. They can keep probing the same final-layer toy setting, which is well understood but omits attention and multi-layer interactions. Alternatively, they can move to small toy transformers, which are closer to real language models but are more complex and less controlled.


A: Stop further work on the toy MLP and unembedding setting and focus on small toy transformers.


B: Continue the investigation using the toy MLP and unembedding setting as the main testbed.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Moving to toy transformers gains realism (attention, multi-layer interactions) but costs tractability and control. Staying with the MLP+unembedding setting keeps rigor and may yield further understanding, but risks limited relevance to real models. The context states the facts neutrally and does not reveal which option was chosen.", "case_for_1": "The minimal setting has already produced its initial understanding, and its omissions (attention, multiple layers) may limit generalization. Moving to small toy transformers tests whether the findings transfer to something closer to real language models, so it is the natural next step for relevance.", "case_for_2": "The final-layer setting is tractable and controlled, and the phenomenon may not be fully understood yet. Deepening that understanding first gives a solid foundation and avoids confounds from the added complexity of transformers, which can make results harder to interpret."}}


### 15dd41aaddfb

A research team is writing an analysis of how long GPUs will keep delivering performance and cost gains for AI workloads. They must decide how strongly to state a prediction about when GPU progress will end. Their reasoning is that gains have depended heavily on shrinking transistor sizes, which face physical and economic limits, while GPUs remain the dominant and cost-effective hardware for most AI workloads and no clear successor is available. The forecast is uncertain, and the team must choose between giving a bounded time window tied to a specific cause and giving no date at all.


A: Decline to give any date for the end of GPU progress, stating that no end is foreseeable soon and GPUs will remain cost-effective.


B: Present the end of GPU progress as a hedged date range, attributing it to limits on shrinking transistor size.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given the stated uncertainty. A hedged date range tied to transistor limits is informative and falsifiable. Declining to give a date avoids false precision when no successor exists and GPUs remain dominant. The context does not reveal which option was chosen. It frames the choice neutrally as a bounded window versus no date.", "case_for_1": "The forecast is uncertain, and GPUs stay cost-effective with no clear successor. Gains can also come from architecture, software, and packaging rather than transistor shrinkage alone. Refusing to give a date avoids overconfident, easily falsified claims. The claim that no end is foreseeable soon is itself a substantive position.", "case_for_2": "The stated reasoning says gains depend heavily on transistor shrinking, which faces physical and economic limits. A hedged range tied to that cause gives readers something concrete, testable, and decision-relevant. Hedging conveys the uncertainty, and naming a specific cause makes the claim more transparent and accountable than having no date."}}


### 9b922901f269

A research team is modelling long-term energy system pathways and must decide how to treat projected future costs of generation technologies, including renewables and nuclear power. Forecasts of technology costs are highly uncertain. Historical cost declines for renewables have followed fairly consistent learning curves, while nuclear costs have shown little systematic decline and have sometimes risen. The team must choose a baseline assumption for how costs evolve, knowing that the choice strongly shapes which technologies appear competitive in the results.


A: Assume historical learning rates persist at roughly constant levels, which makes renewables more competitive than nuclear.


B: Assume a sudden large nuclear cost breakthrough that sharply lowers future nuclear costs below historical trends.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context gives evidence that renewables follow consistent learning curves while nuclear shows no systematic decline. Option 1 extrapolates this evidence into a baseline. Option 2 assumes a sudden, large nuclear breakthrough, which the stated facts do not support. That is a speculative scenario, not a defensible baseline. Nothing in the context offers a trade-off that would justify it as the baseline.", "case_for_1": "It is evidence-based and consistent with historical data. It is transparent and standard for a baseline, and sensitivity analyses can test the alternatives.", "case_for_2": "It could serve as an optimistic sensitivity scenario, or counter a possible bias toward renewables. As a baseline, though, it contradicts the stated historical evidence and has no clear defense."}}


### 7eaa47e9423d

A research team is studying a mechanism whose effects they want to understand in the context of how the future might unfold. Any scenario built on the current status quo carries that status quo's existing flaws, so observed outcomes could come from those flaws rather than from the mechanism itself. The team must decide how to frame the scenarios used in the analysis so that the mechanism's own contribution can be distinguished from the problems of the present situation. The status-quo scenario is not specified in detail, and the team has the option of also defining a separate, explicitly idealized scenario of a good future.


A: Use only the unspecified status-quo scenario and analyze the mechanism within it without defining any idealized good-future scenario.


B: Define an isolated, idealized good-future scenario in addition to the unspecified status-quo scenario to separate the mechanism from the status quo's flaws.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["answer_leak", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "answer_leak", "reason": "The context frames the problem as status-quo flaws confounding the mechanism's effects, then says the team \"has the option of also defining a separate, explicitly idealized scenario.\" That wording points to the second option as the solution. The first option is essentially the confounded approach the context warns against, so the comparison reads as a setup with a signaled answer and not a real trade-off.", "case_for_1": "Using only the status-quo scenario is cheaper and simpler. It is also more policy-relevant and realistic, and an idealized scenario can bring its own arbitrary assumptions. A team with limited resources might accept the confounding and use sensitivity analysis instead. The context, however, presents the confounding as the central problem, which weakens this case.", "case_for_2": "Adding an idealized good-future scenario isolates the mechanism from present-day flaws. Comparing results across the two scenarios shows which effects come from the mechanism and which come from status-quo problems. This directly addresses the stated confound at modest extra cost."}}


### f591bb27bfa0

A research team analyzed historical data on the performance and cost of AI accelerator chips in order to forecast how quickly GPU performance will improve in the coming years. Their data show a long run of rapid yearly gains, and past improvement has been driven largely by transistor miniaturization in field-effect transistor technology. They must decide how strongly to state their conclusion about future gains: whether to rely on a statistical fit to the historical trend, or to make a claim grounded in the physical limits of the underlying transistor technology.


A: State that the analysis strongly suggests improvements become significantly harder in the coming decade, scoped to the field-effect transistor paradigm and justified by miniaturization being the dominant historical driver.


B: Extrapolate a historical experience-curve fit to the chip performance and cost data, and project that rapid yearly gains continue rather than predicting a slowdown tied to transistor physics.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible ways to state a forecast. One rests on physical-limit reasoning and the other on a statistical fit to historical data. Each has a real epistemic basis and a real weakness. The context does not say which to choose, though it hints that miniaturization drove past gains.", "case_for_1": "Past gains came mostly from transistor miniaturization, which faces physical limits. A trend fit cannot see those limits, so a claim scoped to the FET paradigm and grounded in mechanism is more credible. The scoping also hedges the claim, because it does not rule out a new paradigm.", "case_for_2": "An experience-curve fit is empirical and transparent, and it matches the data without speculation about the future. Forecasts of an end to scaling have often been wrong, and the data show a long run of rapid gains. A modest claim that stays close to the observed trend is conservative about what the data can support, and it avoids asserting physical limits the data do not directly test."}}


### 5a80dd5fdbd8

A research team wants to predict GPU performance, including how it will evolve for future devices. They have data on existing GPUs, covering device characteristics such as architectural and hardware features, and measured inference performance across different workloads. Physical miniaturization limits constrain how hardware features can keep changing over time. The team must choose a modeling approach that captures the relationship between hardware characteristics and performance and is accurate enough to be useful for prediction.


A: Build a composite model that combines a performance model linking GPU features to performance with a feature model projecting how those features change over time under miniaturization limits.


B: Train supervised regressors, chiefly tree-based ensembles such as extra-randomized trees and XGBoost, to predict inference performance directly from device and workload features.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The two options target different scopes. Option 1 can forecast future GPUs by projecting features forward, so it addresses the stated goal directly. Option 2 is a simpler and likely more accurate model of existing devices, but it has no way to project feature evolution. Neither option is plainly inferior, and the context does not state which one to choose.", "case_for_1": "The goal explicitly includes predicting how performance will evolve for future devices. The composite model separates the feature-to-performance mapping from a feature-evolution model that respects miniaturization limits, which gives a principled way to extrapolate beyond the observed range. Tree ensembles cannot extrapolate on their own.", "case_for_2": "Tree ensembles such as extra-trees and XGBoost are strong on tabular data and need little feature engineering. They are likely to give high accuracy on the available data. The feature-projection step in Option 1 adds uncertainty, and with few GPU generations it may be poorly determined. Option 2 can also serve as the performance-model component, and future feature values can be supplied as scenarios."}}


### f9c074f9a1f8

A research team ran an initial survey and found that respondents expressed high agreement with a set of conflict resolution mechanisms. The team now needs to decide what evidence to gather to judge whether this finding reflects a genuine pattern or is an artifact of confounding factors, question framing, or random variation. The original result is in hand, and the team can either treat the existing survey instrument as sufficient or collect further evidence to probe how stable the finding is.


A: Run robustness tests with reworded questions, then adversarial tests designed to elicit lower agreement with the mechanisms.


B: Rely on the original survey wording alone to support the finding of agreement with the conflict resolution mechanisms.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the team wants to judge whether the finding is genuine or an artifact of confounding, question framing, or random variation. Option 2 relies only on the original wording, which cannot address framing or stability concerns and so does not serve that goal. Option 1 (reworded questions plus adversarial tests) directly tests those threats. Option 2's only advantage is saving cost and effort, which is not a meaningful trade-off given the stated aim.", "case_for_1": "Reworded and adversarial questions directly probe framing effects and acquiescence bias. They show whether the agreement holds up, which is exactly the evidence the stated goal calls for.", "case_for_2": "The only case is resource savings, such as a tight budget, or a belief that the instrument was already validated. Neither is stated, and relying on the same wording cannot answer the question of whether the result is an artifact."}}


### f23f4f65ed75

A research team surveyed participants about how much they agreed with several mechanisms and also asked how strongly they expected each mechanism to converge to their own view over time. Across mechanisms, agreement correlated positively with expected convergence to the participant's view. The team had to decide how to interpret this relationship, given that the measured correlations were moderate in size and all fell below one half.


A: Conclude that expected convergence accounts for only part of the agreement, leaving a substantial portion unexplained by it.


B: Conclude that expected convergence accounts for all of the agreement, leaving no portion unexplained by it.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "With moderate correlations all below 0.5, shared variance is under 25%. This directly contradicts the claim that expected convergence accounts for all of the agreement. Option 2 is plainly unsupported by the stated facts, and there is no real trade-off between the two options.", "case_for_1": "Correlations below 0.5 mean r² is under 0.25, so expected convergence explains at most a quarter of the variance in agreement. Most of the variance is left unexplained. The correlation is also not evidence of causation, which makes the conclusion appropriately cautious.", "case_for_2": "None. A correlation below one half cannot show that one variable fully accounts for the other. Full explanation would require a correlation near 1 (after accounting for measurement error), and the stated data do not suggest that."}}


### 0df294083fba

A research team surveyed respondents about a set of proposed mechanisms and found a high level of agreement with them. Two explanations were available for this pattern. Respondents may have tended to agree with statements regardless of their content (acquiescence bias). Alternatively, the pattern may reflect respondents' own views, with the team expecting the results to match those views. The survey items were fairly general, and the team had to decide how to interpret the agreement in their analysis.


A: Interpret the high agreement with the mechanisms as stemming from acquiescence bias among respondents rather than from genuine agreement.


B: Interpret the high agreement as only mild evidence of robust agreement, and plan a later survey with more detailed scenarios to double-check.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible interpretations of ambiguous survey data. The context offers two competing explanations and does not say which is correct. Option 1 commits to acquiescence bias. Option 2 treats the agreement as mild evidence of genuine agreement and plans a follow-up. The options differ in how much they commit to a reading and in how much effort they spend on verification.", "case_for_1": "The items were fairly general, which invites agreement whatever the content. The team also expected the results to match respondents' views, which is a reason to be skeptical of the pattern. Discounting the agreement as acquiescence is a conservative choice that avoids overclaiming, and it costs nothing extra.", "case_for_2": "The context gives no evidence that settles the question, so declaring the agreement to be acquiescence is itself an overclaim. Treating it as weak evidence and following up with detailed scenarios, which are less prone to acquiescence, is a calibrated approach that can separate the two explanations. The cost is a second survey."}}


### f744602dbceb

A research team is running a survey-based study on why people resist changing their minds when presented with hypothetical scenarios (counterfactuals) that might alter their views. A concern has been raised that the observed unwillingness to change minds could be an artifact of the specific counterfactuals the researchers selected, since these may not match what respondents actually find relevant or persuasive. The team must decide how to select the counterfactuals for the final poll so as to address this concern.


A: Select the counterfactuals for the final poll directly by researcher judgment, without any preliminary testing with respondents.


B: Select the final poll's counterfactuals by running earlier survey versions with free-form responses and keeping those respondents cared about most.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The stated concern is that researcher-chosen counterfactuals may not match what respondents find relevant, which could make the observed resistance an artifact. Option 1 leaves that concern unaddressed, because researcher judgment with no respondent input is the very practice being questioned. Option 2 responds to the concern directly by using pilot free-form responses to identify the counterfactuals respondents care about. Option 1 does save time and money, but the context gives no constraint that would make those savings a real trade-off against answering the concern.", "case_for_1": "It is cheaper and faster, and it avoids pilot rounds that could introduce their own selection biases. A team with strong theory or prior literature could argue that expert-chosen counterfactuals are more standardized and comparable. Still, this does not respond to the stated concern, so the case is weak.", "case_for_2": "Piloting with free-form responses grounds the counterfactuals in what respondents themselves find relevant and persuasive. That directly tests whether resistance to changing minds is an artifact of researcher selection, and it makes the final poll's findings more credible."}}


### 8d13fc72df4a

A research team ran a study in which participants judged scenarios involving a decision-maker and indicated how much they agreed with the decision-maker's choices. In one condition the decision-maker was a future human, and in another it was a future AI. Participants showed much lower agreement in the future AI scenario than in the future human scenario. The team had to decide how to interpret this gap. The data did not separately show whether the AI's choices were correct in each case, so the lower agreement could reflect either a general difference in trust toward the two kinds of decision-makers or a context-sensitive tendency to disagree with an AI that might be wrong.


A: Interpret the lower agreement with the AI as evidence that participants trust human decision-makers much more than they trust AI decision-makers.


B: Interpret the lower agreement with the AI as potentially appropriate, calibrated reliance, because disagreeing is better when the AI is wrong, and not as general distrust.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says the data cannot separate general distrust from context-sensitive disagreement with a possibly wrong AI. Option 1 asserts general distrust as the interpretation, which the data do not support. Option 2 is also somewhat overreaching, since it claims the gap is appropriate and not distrust. But it is hedged with 'potentially', and it fits the missing correctness data better. Option 1 is the less defensible of the two.", "case_for_1": "The gap was large and consistent with the common finding of algorithm aversion. Without correctness data, the simplest reading is a general trust difference. Reading it that way is a cautious default for flagging adoption risks. However, it ignores the stated ambiguity and treats one hypothesis as established.", "case_for_2": "Without ground truth on whether the AI was right, lower agreement may reflect healthy skepticism. The 'potentially' framing keeps the claim tentative and acknowledges that the data cannot rule out calibration. This option matches the stated uncertainty better than a firm claim of distrust."}}


### e079873ef385

A research team ran a follow-up to an earlier survey study whose results might have been shaped by participants giving socially desirable answers. In the follow-up, one condition added a reminder urging participants to answer truthfully, and this reminder produced no measurable change in responses. Another condition, in which the framing of the abortion item was reversed, produced a drop in agreement. The team had to decide how to interpret this pattern of a null effect from the truthfulness reminder alongside the decline in agreement under the reversed abortion framing, specifically what it implies about the original findings and about whether the mechanism and the outcome in the original study can be cleanly separated.


A: Conclude that participants already answered truthfully in the original study and that the mechanism and outcome are not fully decoupled.


B: Conclude that social desirability bias explains the original results and that participants did not answer truthfully.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are interpretations of an ambiguous pattern. A null truthfulness reminder could mean participants were already honest, or that the reminder is too weak to counter desirability bias. The framing effect shows responses are sensitive to wording, which supports the claim that mechanism and outcome are entangled. It could also be read as evidence of desirability pressure. Neither option is plainly inferior or leaks the answer.", "case_for_1": "A null reminder effect is what you would expect if participants were not strategically misreporting. The framing-driven drop shows that responses depend on item wording, so the mechanism and outcome cannot be cleanly separated. This is a cautious reading that does not over-claim.", "case_for_2": "Reminders to be truthful are known to be weak against social desirability bias, so the null result is not strong evidence of honesty. The drop in agreement under reversed framing is consistent with desirability or acquiescence pressure shaping answers. On this reading the original results were substantially biased. This reading is more assertive than the evidence strictly supports, but it is still defensible."}}


### 1f9313ae4896

A research team ran an experiment in which participants evaluated a decision-making mechanism under several conditions. In the baseline setting, participants showed high agreement with the mechanism's outputs. In the conditions where the decision-makers held different political views, held different moral views, or had flaws made salient, participants' agreement dropped noticeably relative to baseline. The team had to decide how to explain this reduced agreement. The reduction could reflect participants using their agreement with, or trust in, the decision-makers as part of how they judged the mechanism. It could also reflect participants' own bias and motivated reasoning, with scrutiny from an opposing party exposing flaws in their beliefs.


A: Interpret the reduced agreement as participants judging the mechanism partly by how much they agree with or trust the decision-makers.


B: Interpret the reduced agreement as bias and motivated reasoning exposed by opposing scrutiny, not as a judgment of the decision-makers' trustworthiness.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context presents two competing explanations for the drop in agreement, and the stated facts do not favor either one. Both are plausible interpretations of the same data. Neither is plainly inferior, and the context does not say which was chosen.", "case_for_1": "Agreement fell specifically when the decision-makers differed in politics or morals or had their flaws made salient. That pattern fits participants using trust in or agreement with the decision-makers as an input to judging the mechanism. It is also the more parsimonious reading, since the manipulation targeted the decision-makers.", "case_for_2": "Motivated reasoning is well documented. Scrutiny from an opposing party can expose weaknesses in participants' own beliefs and lower their agreement, with no change in how they judge the decision-makers' trustworthiness. This reading also fits the drop appearing across several different conditions, and it avoids treating the drop as a rational judgment about trust."}}


### a5d2a7f5bf7a

A research team studied how a decision-support mechanism shapes human reliance on AI recommendations. In the study, participants agreed with the AI less often under one condition than under another. This pattern is ambiguous. It could reflect participants placing more confidence in human judgment, or it could reflect a property of the mechanism that reduces agreement with the AI whoever the decision-maker is. The data on their own do not separate these readings, and the team must decide how to interpret the lower agreement.


A: Interpret lower agreement with the AI as trust in humans and treat the results as dependent on the decision-maker rather than on the mechanism itself.


B: Interpret lower agreement with the AI as a direct effect of the mechanism itself and treat the results as general across decision-makers.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 5, "votes": ["a", "a", "b", "a", "a", "b", "b", "b", "a", "b"], "quality": {"category": "dominated", "reason": "The context says the data cannot separate the two readings. Both options nonetheless commit fully to one interpretation and claim a generalization the data do not support. Neither mentions a way to resolve the ambiguity, such as a control condition or an additional experiment. The choice is between two equally unsupported conclusions, which is a weak comparison, though not clearly dominated. Each reading is plausible, and a team might provisionally adopt either one, but the framing pushes an unwarranted certainty. Because the context says the question is genuinely ambiguous, the options are roughly symmetric guesses rather than a real trade-off between priorities.", "case_for_1": "Being cautious about the mechanism's generality is the conservative choice. Treating the result as decision-maker dependent avoids overclaiming that the mechanism works universally. It also fits the literature on algorithm aversion and on people's preference for human judgment.", "case_for_2": "Attributing the effect to the mechanism is the more parsimonious reading when the mechanism is the manipulated variable. Participants were assigned to conditions, so the difference is causally tied to the mechanism. Claiming generality across decision-makers is a reasonable working hypothesis until it is falsified."}}


### 5930ed6440cb

A research team has completed a study on how AI systems should handle questions of value choice, meaning which values an AI should be built to follow. The results suggest that the usual framing of the problem as selecting the right values may be incomplete, and that an alternative framing based on designing mechanisms by which values are determined and revised could fit the findings better. The team must now decide how strongly to state the implication of these results for the framing of AI value choice in the write-up. The results are suggestive and bear on the framing, but they are not a formal demonstration that one framing is correct.


A: Assert flatly that the goal should shift from value alignment to ensuring humanity keeps control over its future, as a plain claim about what is wanted.


B: State that the results provide evidence for mechanism design being a better frame than value choice, without claiming they prove it.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says the results are suggestive but not a formal demonstration. Option 2 matches that evidential status. Option 1 asserts a flat normative claim, and it also shifts to a different framing, 'humanity keeps control over its future', rather than the mechanism-design framing the results supported. That overstates the findings and misstates the implication. Few plausible priorities would favor it.", "case_for_1": "Bold, clear claims can provoke discussion and shift the field's framing. An author could argue the goal is a normative position the paper is entitled to advocate. Even so, the claim goes beyond what the results support and swaps in a different framing, so this case is weak.", "case_for_2": "It is calibrated to suggestive evidence, it names the specific alternative framing the results favor, and it avoids claiming proof. This protects credibility while still making a substantive, useful claim."}}


### 54a0a0ec3395

A research team is studying public sentiment toward AI systems acting as decision-makers in society. They have already built a set of survey questions about a hypothetical future society, where humans hold decision-making roles, and they must now decide what evidence to collect on attitudes toward AI in those roles. One approach is to pose new questions about AIs that use a different framing. Another approach is to retain the same future-society assumptions and questions and only replace the human decision-makers with benevolent AIs, so that responses can be compared directly across the two conditions.


A: Keep the future-society assumptions, replace humans with benevolent AIs, and ask respondents the identical original questions.


B: Ask respondents about AI decision-makers using new questions with a different framing from the original survey.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Option 1 gives a controlled comparison with the human-decision-maker baseline, so any differences in responses can be attributed to the swap. Option 2 trades that comparability for new framings that may capture aspects of attitudes the original questions miss. The context describes both approaches neutrally and does not state which one to take.", "case_for_1": "Identical questions and assumptions isolate the effect of the decision-maker being human versus AI. This gives a clean, directly comparable result at low design cost, and it avoids confounding from changed wording.", "case_for_2": "New framing questions can reveal attitudes that a human-centered question set would miss, such as concerns specific to AI like opacity, control, or values. They may also avoid anchoring on assumptions built for humans, and they give a broader, more exploratory view of sentiment, which is useful if the original questions fit AI poorly."}}


### 648aa2d52630

A research team is preparing a large survey of adults in the United States about a scenario involving artificial intelligence. Before the main data collection, they ran four small trial runs of the questionnaire. In each of these, the responses showed that participants misunderstood the text describing the AI scenario. The team must now decide whether the current survey instrument is adequate to launch on the full sample of about 1000 participants, or whether further changes are needed first.


A: Launch the main survey with an earlier version of the scenario text, despite the misunderstanding seen in the four trial runs.


B: Revise the questionnaire and repeat trial runs until participant answers show they understand the scenario, then launch the main survey.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says four pilots all showed participants misunderstood the scenario text. Launching a 1000-person survey with a known-misunderstood scenario would produce invalid data. Option 1 also uses an 'earlier version' of the text, which is the version that failed in the pilots. No stated fact (such as a deadline, budget cap, or irreversible launch window) makes this a reasonable trade-off against fixing the instrument first.", "case_for_1": "Only under unstated conditions: a hard deadline or exhausted budget, or the misunderstanding being irrelevant to the key outcome. The context gives none of these, so the case is very weak.", "case_for_2": "Iterating on the wording until pilot participants understand the scenario protects the validity of a costly 1000-person survey. The extra pilots are cheap compared with wasting the main sample on misread stimuli."}}


### 7546ddc38835

A research team wants to measure public attitudes toward AI systems operating in several concrete real-world settings. They plan a survey with about 1000 participants who see varied instruction sets describing the scenarios. The central design question is how to word the attitude question. Two natural phrasings exist: one asks what AI should be allowed or expected to do (a normative 'should' framing), and the other asks how much respondents trust AI in that setting (a 'trust' framing). Each phrasing may carry its own response biases, and it is unknown how far the results depend on wording. The team must decide how to elicit attitudes so the evidence collected is as informative and robust as possible.


A: Ask every participant about each concrete AI setting using only one phrasing, either 'should' or 'trust', across the whole survey.


B: Ask every participant about each concrete AI setting using both the 'should' and 'trust' phrasings to reduce the influence of wording biases.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible designs. Option 1 uses a single phrasing, which avoids order and consistency contamination and keeps the survey short. Option 2 asks both phrasings, which allows direct testing of wording dependence and robustness, but risks carryover effects and respondent fatigue. The context does not make either choice clearly inferior.", "case_for_1": "One phrasing per participant, whether randomized between participants or fixed, avoids priming and demand effects where answers to the second question are anchored on the first. It shortens the survey, lowers fatigue and dropout, and gives cleaner estimates of each framing. If framing is randomized across the 1000 participants, wording dependence can still be estimated between subjects.", "case_for_2": "Asking both phrasings within subject lets the team measure how much results depend on wording at the individual level, which the context says is unknown. It gives more statistical power per participant and yields a direct comparison of should versus trust. Randomizing the order controls much of the carryover, which makes the evidence more informative and robust."}}


### 2dab8bce69f9

A researcher interested in AI alignment is deciding how to direct their own work. They have read a long document laying out an agenda for a science of deep learning, which proposes understanding how neural networks train, generalize and behave through empirical and theoretical investigation, and lists many concrete project ideas. The agenda is plausibly useful for alignment, but its payoff is uncertain and it competes with other alignment research directions for the researcher's limited time. The researcher must decide whether to personally commit to this agenda and take up some of its project ideas, or to put their effort into other approaches to alignment.


A: Decline the science of deep learning agenda and pursue other approaches to alignment instead.


B: Commit to the science of deep learning agenda and pursue some of its listed project ideas soon.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context presents real uncertainty: the agenda is plausibly useful for alignment but has an uncertain payoff and competes with other directions for limited time. Committing to it and pursuing other approaches are both reasonable, and the choice depends on the researcher's priorities, comparative advantage and risk tolerance. The context does not say which to pick.", "case_for_1": "Payoff is uncertain and time is limited. Other alignment approaches may be more directly targeted, better matched to the researcher's skills, or less crowded. Declining avoids diffusing effort into a broad agenda that only plausibly helps alignment.", "case_for_2": "The agenda is concrete, offers many ready project ideas, and is plausibly useful. Understanding how networks train and generalize could underpin many alignment approaches. Committing early lets the researcher build expertise and make tangible progress instead of staying uncommitted."}}


### 5ddda6c8acd6

A team developing advanced AI systems considered how an AI's guiding values should be chosen. One candidate approach was a default in which the developing company itself decides those values. In public polling about possible ways to choose AI values, this company-chooses default performed poorly compared with the alternatives. The team had to decide how to interpret this weak result: whether it reflected a considered public rejection of the approach or something more superficial, such as limited familiarity with it or distrust of how it was framed. The interpretation would shape what the team did next about the default and about how AI values get chosen more broadly.


A: Treat the poor polling as unfamiliarity and distrust of the framing, keep the company-chooses default as a fallback, and invest in transparency and public input to build its legitimacy.


B: Treat the poor polling as a sign that better methods for choosing AI values are needed, since inaction in advance would produce the least preferred outcome.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible readings of weak polling. Option 1 discounts the result as shallow (unfamiliarity or framing distrust) but still invests in legitimacy-building. Option 2 treats the result as a real signal and pursues better methods for choosing values. The context does not say which reading is correct, and neither option contradicts the stated facts. The options partly overlap, since both involve public input, but they differ on whether the default remains the fallback and how much the poll is trusted.", "case_for_1": "One poll with possible framing effects is weak evidence of considered rejection. A fallback is practically necessary because someone must set values if no broader process exists. Transparency and public input address the legitimacy concern directly while keeping the team able to act.", "case_for_2": "The public consistently disliked the default, so taking that at face value is cautious. Waiting to develop better collective methods now avoids being stuck with the least preferred outcome by default. This is more responsive to democratic legitimacy concerns than rationalizing the result away."}}


### e27002f3f9a6

A research team is writing about approaches to specifying values for advanced AI systems by having an agent or process reflect, extrapolate, or otherwise refine preferences over time, rather than fixing values directly. Their analysis suggests that such reflection-based procedures may converge on good values across many starting conditions, but they have not systematically searched for cases where the procedures diverge, get captured by flawed starting points, or produce bad outcomes. Evidence is largely conceptual and based on a limited set of examples. They must decide how strongly to state their conclusion about whether these procedures produce robustly good values.


A: Assert that reflection-based approaches yield robustly good values, and present the conclusion as established without caveats about adversarial cases.


B: State only cautious optimism that reflection-based approaches may yield robustly good values, and flag the need to search for adversarial cases where robustness fails.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context states the evidence is conceptual, based on limited examples, and that no systematic search for divergence or capture has been done. Option 1 asserts the conclusion as established and drops all caveats, which overclaims relative to that evidence. Option 2 matches the evidence by stating cautious optimism and flagging the need for adversarial search. There is little real trade-off, because stating an unsupported conclusion as established is not defensible here.", "case_for_1": "A team could argue that a clear, confident claim gives a strong thesis, draws attention, and provokes critique. It might also say the conceptual argument is persuasive. But dropping all caveats about untested adversarial cases is hard to justify given the stated evidence.", "case_for_2": "Calibrated wording matches the limited, conceptual evidence. It tells readers where the analysis is weak, and it points to concrete follow-up work on divergence and capture. This protects credibility and is appropriate in a safety-relevant area."}}


### dd0a81c047e8

A research group is setting up a Science of Deep Learning agenda whose purpose is to support AI safety and alignment. It must decide how to scope eligible projects. Some candidate projects would improve general understanding of how deep networks learn and behave, with only an indirect or speculative link to safety. Others would offer a clear and direct safety benefit. Requiring a direct safety link would keep the agenda tightly focused on its mission, but it could exclude foundational work that might later prove useful for alignment. Allowing general-understanding work would widen the pool of projects and the potential for foundational insight, but it could dilute the focus on safety outcomes.


A: Restrict projects to those that offer a direct safety benefit, excluding work aimed only at general understanding of deep learning.


B: Accept projects that target general understanding of deep learning as a starting point, while preferring those with direct alignment benefit where possible.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both scoping policies are reasonable. A strict direct-safety filter keeps the agenda focused on its mission. A broader policy that still prefers direct alignment benefit captures foundational insight at some cost to focus. The context lays out the trade-off evenly and does not say which to choose.", "case_for_1": "The agenda exists to support safety, and resources are limited. A strict filter prevents drift into generic deep learning science that other groups already fund. It keeps projects accountable to safety outcomes and makes evaluation easier, since speculative links are easy to overclaim.", "case_for_2": "Foundational understanding of how networks learn may be necessary for durable alignment solutions, and its safety relevance often becomes clear only later. Accepting it while preferring direct benefit widens the pool and keeps a safety-oriented priority, which limits the dilution risk."}}


### ef1253ecb6df

A researcher is presenting a new research agenda in AI alignment and must decide how strongly to state its promise relative to other alignment approaches. The field currently concentrates most of its effort on a few dominant approaches, and the researcher has real uncertainty about how well the new agenda will work compared with those alternatives. The framing chosen will shape how the agenda is received and whether it prompts others to explore additional directions.


A: Express excitement about the agenda while explicitly stating uncertainty about how promising it is compared with the alternative approaches.


B: Concede that the dominant approaches have a reasonable chance of working, and argue that the field is over-concentrated on them and should diversify into new agendas.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both framings are honest and defensible given the researcher's real uncertainty. Option 1 foregrounds enthusiasm and calibrated uncertainty about the agenda itself. Option 2 makes a portfolio-level argument for diversification while acknowledging that the dominant approaches might work. They differ in emphasis and rhetorical strategy, and neither is clearly inferior. The context does not reveal which one was chosen.", "case_for_1": "It is the most epistemically direct framing. It conveys the researcher's real excitement and real uncertainty without making claims about the whole field. It avoids appearing to criticize others, which may help reception and collaboration, and it invites scrutiny of the agenda on its merits.", "case_for_2": "It addresses the stated goal of prompting others to explore additional directions. The diversification argument holds even if the agenda is uncertain, because under uncertainty a portfolio is worth more than concentrated effort. Conceding that the dominant approaches might work keeps the argument credible and calibrated while still making a clear case for change."}}


### a4dda4375447

A research group works on mechanistic interpretability, the study of the internal computations of neural networks. The group expects this work to help alignment by making models easier to understand and oversee. It also recognizes that some findings could speed up capabilities progress by suggesting better architectures, training methods, or optimization techniques. Publication norms for the field are not settled, and the group must set a policy for how widely to share its results. The policy must weigh the benefits of open scientific exchange, such as faster collective progress, outside scrutiny, and wider adoption of safety-relevant tools, against the risk of accelerating capabilities.


A: Circulate high-capabilities-potential work only among a few trusted people and publish low-potential work widely.


B: Publish all mechanistic interpretability work openly and widely, regardless of its potential to advance capabilities.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "This is a real tension in the publication policy of an interpretability group. Both options are defensible under the stated facts, and neither reveals a recorded action.", "case_for_1": "Selective sharing keeps most of the benefits of openness for work that is mostly safety-relevant. It withholds findings that could speed up capabilities, which the context names as a real risk. Many safety researchers endorse this kind of differential-publication policy. Its weakness is that judging 'capabilities potential' is hard, but a trusted-circle review can manage that.", "case_for_2": "Full openness gives the fastest collective progress, outside scrutiny, and wide adoption of safety tools. It avoids the unreliable task of predicting which findings will help capabilities. It also avoids the risk that a closed group slows the whole field's safety progress. Interpretability may help alignment more than it helps capabilities, and capabilities gains may come anyway from other sources. A researcher who holds these views could reasonably prefer a simple, predictable open norm."}}


### 27bd3ea3580c

An independent researcher, working without an institutional supervisor or formal deadlines, must decide how to organize their research practice. The goal is to make steady progress and remain accountable to themselves and to a wider audience. Without external structure, there is a risk of drifting, spending long periods on unfocused investigation, or never finishing anything shareable. Two broad ways of organizing the work are available: one treats research as open-ended exploration where the direction is followed wherever curiosity leads, and the other fixes a concrete deliverable at the outset and works toward it.


A: Commit at the start to publishing a post that answers the research question, even if the answer is a negative finding.


B: Treat the research as open-ended exploration, following findings wherever they lead with no planned outcome or deliverable.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["answer_leak", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "answer_leak", "reason": "The context frames open-ended exploration as the source of the problem (drifting, unfocused investigation, never finishing anything shareable). It also states the goal as steady progress and accountability to a wider audience, which only a committed deliverable serves. Together these effectively tell the reader to choose option 1. Option 2 is a strawman that conflicts with the stated goal, so the comparison offers no real trade-off.", "case_for_1": "A committed deliverable gives structure, accountability, and a finish line, and it directly addresses the stated risks. Accepting a negative finding keeps the commitment honest and avoids forcing a particular result.", "case_for_2": "Open-ended exploration can lead to unexpected discoveries and suits early-stage curiosity-driven work. Still, the stated goals of steady progress and accountability, and the stated risk of never finishing anything shareable, leave little room to defend it here."}}


### 9fe971b7acae

A research team is weighing whether work on mechanistic interpretability could speed up AI capabilities, which would make publishing and promoting it a safety concern. Historically, mechanistic interpretability research has produced few or no measurable gains in AI capabilities. The team must decide what this track record implies. One reading treats it as evidence about how risky the field is. The other treats it as evidence about how developed the field is.


A: Treat the absence of capabilities gains as evidence that interpretability research is safe to pursue and publish.


B: Treat the absence of capabilities gains as a sign that interpretability is too immature to be useful, not as evidence of safety.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context presents two genuinely competing interpretations of the same track record (low risk vs. low maturity), and the facts do not decide between them. Option 1 favors openness and Option 2 favors caution about future capability gains as the field matures. Neither contradicts the stated facts. The context frames the dilemma neutrally and does not reveal a recorded choice.", "case_for_1": "Empirical track record is the best available evidence. Years of work with no measurable capabilities gains suggest the transfer risk is low. Treating absence of evidence as non-reassuring would block almost any research. Publishing speeds safety progress, and a precautionary stance has real costs in lost collaboration and slower alignment work.", "case_for_2": "A field that has not yet produced useful results tells us little about what a mature version could do. Interpretability could eventually inform architecture, training, or debugging, which would speed capabilities. Because publication is irreversible, it is prudent not to treat past immaturity as a safety guarantee and to keep case-by-case scrutiny of what gets promoted."}}


### 39d60648e095

A research team working on neural network interpretability is deciding whether to make superposition a main priority. Superposition is the phenomenon where a model represents more features than it has dimensions, and it is widely seen as a central obstacle to decomposing models into understandable parts. A better understanding of it could help safety work by making model internals more legible. It could also give insight into how models store and compute information efficiently, which might speed up capabilities progress. The team has no firm evidence on how large either the safety benefit or the capabilities externality would be, and it must decide whether the potential risk should shape its research priorities.


A: Deprioritize superposition research and pursue other interpretability directions to avoid contributing to capabilities progress.


B: Prioritize superposition research and accept the capabilities risk because the expected safety benefit of understanding it is larger.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible under the stated uncertainty. One weighs the possible capabilities externality more heavily and avoids it. The other weighs the safety value of a central obstacle more heavily. The context does not say which action to take. The second option asserts that the safety benefit is larger, but this is a rationale the team could hold, not a fact given in the context.", "case_for_1": "The team has no evidence that the safety benefit outweighs the capabilities risk. Other interpretability directions could still yield progress, and capabilities speedups are hard to reverse. Under a precautionary stance it is reasonable to avoid a direction with possible dual-use externalities.", "case_for_2": "Superposition is widely seen as a central obstacle to decomposing models, so progress on it could unlock much of interpretability's safety value. Capabilities insights are speculative and may come from elsewhere anyway. Avoiding the work could leave safety-relevant understanding behind, so prioritizing it is a reasonable bet."}}


### a4c14469d8d4

A research team has proposed a mechanistic hypothesis about how a trained neural network performs a specific task, attributing the computation to a particular set of neurons and the features they encode. Ablation experiments on these components have already been run and are consistent with the hypothesis. The team wants a further test that goes beyond ablations to check whether the hypothesis fully accounts for the model's behavior. They must choose which kind of intervention to use for validation, knowing that the choice affects how strictly the hypothesis is tested and how informative the results are about whether the proposed explanation is sufficient.


A: Validate the hypothesis by zero-ablating the neurons the hypothesis identifies and measuring the effect on model behavior.


B: Validate the hypothesis by running a causal scrubbing test that resample-ablates all neurons at once and scans a range of similarity thresholds.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says ablation experiments have already been run and the team wants a test that goes beyond ablations to check whether the hypothesis fully accounts for the behavior (sufficiency). Option 1 is simply another zero-ablation, which repeats what was done and tests necessity rather than sufficiency. Option 2 (causal scrubbing) directly addresses the stated goal. Option 1 offers no meaningful trade-off beyond minor simplicity, and that does not outweigh failing the stated need.", "case_for_1": "Zero-ablation is cheap, simple, and easy to interpret. It could be run on additional components for robustness. However, it duplicates the existing ablations and does not test sufficiency, so the case is weak.", "case_for_2": "Causal scrubbing resamples activations according to the hypothesis and tests whether the proposed computation is sufficient to account for behavior. It is stricter and more informative, and scanning thresholds shows how the result depends on the similarity criterion. This matches the stated goal."}}


### d13edbea75aa

A research team projected high-dimensional data onto its leading principal components and saw a V-shaped distribution of points. The shape indicated that the structure relevant to their question did not lie along the principal component axes, but along two separate arms of the V. They needed to choose a coordinate basis for the subsequent analysis. One basis is the PCA eigenvectors, which capture the directions of greatest variance. The other is a pair of directions aligned with the two arms of the V, which a quick linear regression on each arm can estimate.


A: Carry out the further analysis in the basis of the PCA eigenvectors, which capture the directions of greatest variance.


B: Carry out the further analysis in the basis of two arm directions, which quick linear regression on each arm of the V estimates.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context states that the structure relevant to the question lies along the two arms of the V and not along the PC axes. It also says the arm directions are cheap to estimate with quick regressions. This leaves no real cost or benefit to weigh against the arm basis, so the PCA basis is plainly inferior for the stated goal.", "case_for_1": "PCA is the standard orthonormal basis and is unique and reproducible, with no choices about how to fit the arms. Arm directions from regression may be non-orthogonal or noisy, and PCA may be easier to interpret and compare with other work. However, the context says the relevant structure is not along PC axes, so these points are weak.", "case_for_2": "The arms hold the structure relevant to the question, and the context says they can be estimated cheaply with a linear regression on each. Working in that basis aligns the analysis with the signal. Its main risk is that the arm directions may be non-orthogonal or estimated with error."}}


### 2060343570d9

A research team is studying a set of neurons that act as detectors for a particular input feature, including a subgroup that responds to the absence or opposite of that feature. They want to test the causal role of these detectors by ablating them. The standard approach of setting activations to zero was tried first and failed to give meaningful results, because the subgroup of opposite-feature detectors has a baseline activation below zero, so zeroing moves those neurons away from their no-detection state rather than toward it. The team must now choose a different ablation scheme for the detector neurons.


A: Set each detector neuron's activation to its minimum value over the dataset, treating that minimum as the no-detection baseline.


B: Set each detector neuron's activation to zero during the ablation, treating zero as the no-detection baseline for every neuron.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says zero-ablation was already tried and failed because the opposite-feature neurons have a negative baseline, so zero is not their no-detection state. The second option repeats that failed approach. The first option, minimum-value ablation, is a direct response to the stated problem.", "case_for_1": "It addresses the identified failure. Setting each neuron to its dataset minimum approximates a neuron-specific off state, including for neurons with a negative baseline. It is simple to apply and is a plausible fix, though the minimum could be an extreme value rather than the true baseline.", "case_for_2": "Zero ablation is the standard method and is simple and comparable with earlier work. But the context says it already failed here for the stated reason, so no defensible case remains for choosing it as the new scheme."}}


### 3bd71ac81bfc

A research team was interpreting a model by examining a two-armed structure of images, with a clue image at the center and a right arm and a left arm extending outward from it. The clue image was a handwritten digit '1'. Following up on the furthest-out example in the right arm gave a working hypothesis about what the model was responding to. Applying the same follow-up to the furthest-out example in the left arm did not produce a hypothesis that held. Visualizations of the relevant neurons for the left arm looked like the opposite of a '1', suggesting that the left arm might encode something related to the clue image by inversion rather than by direct resemblance.


A: Drop the furthest-out left-arm image and test the inverted clue image, computed as one minus the clue image, as the explanation for the left arm.


B: Keep the furthest-out left-arm image as the focus and test it directly as the explanation for the left arm, as was done for the right arm.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the direct follow-up on the furthest-out left-arm image already failed to yield a hypothesis that held, and neuron visualizations point to inversion. Option 2 repeats the failed approach, while Option 1 follows the evidence. Option 2 has no real trade-off in its favor.", "case_for_1": "Direct testing already failed on the left arm, and the neuron visualizations look like the opposite of a '1'. Testing the inverted clue (1 minus the clue image) is a targeted, cheap hypothesis that fits the evidence and could explain the left arm.", "case_for_2": "Weak: one could argue the first attempt was under-tested or that the inversion idea is speculative and shouldn't replace the symmetric procedure. But the stated facts say the direct test did not hold, so rerunning it adds little."}}


### d39e66171dda

A team is building a benchmark that measures situational awareness in language models through several task categories. Most categories can be scored automatically, so their results combine into a single aggregate score that can be computed cheaply and reproduced exactly by anyone. One category, which asks models to produce a long free-form monologue, can only be graded by human raters. Human grading is slower, costlier, and less reproducible across users of the benchmark. The team must decide whether this category's results should feed into the aggregate score or be handled separately.


A: Offer the human-graded category as an optional bonus task and leave it out of the aggregate score.


B: Include the human-graded category in the aggregate score alongside the automatically scored categories.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both choices are defensible. Excluding the human-graded category keeps the aggregate cheap and exactly reproducible. Including it gives fuller construct coverage but weakens those properties. The context states the costs without recommending either choice.", "case_for_1": "The aggregate stays cheap, fast and exactly reproducible by anyone, which is what makes a benchmark widely adopted and comparable. The human-graded task is still available for those who can afford it, and its noisy, costly scoring does not contaminate the headline number.", "case_for_2": "If long-form monologue is central to situational awareness, leaving it out makes the aggregate less valid and easy to game, because models could be optimized only on the automatic tasks. Including it keeps the full construct in the headline score. Standardized rubrics, rater training or a fixed set of released grades could reduce the reproducibility problem."}}


### f020742d1491

A research team evaluates whether language models display situational awareness, using a Long Monologue task in which the model produces extended free-form text that is scored for correct self-identification as an AI system. A pretrained base model with no instruction tuning receives an above-zero score on this task. A concern arises that this score may not reflect genuine situational awareness and may instead result from the model frequently mentioning AI or language models in its output regardless of the prompt. The team must decide how to address this concern about the base rate of AI references.


A: Sample the base model's responses to prompts unrelated to AI or language models and check how often they contain AI references as a control.


B: Explain the base model's self-descriptions as a product of leading prompts that cue AI-related answers, without testing its output base rate on unrelated prompts.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The team needs to address a concern that the score reflects a high base rate of AI references. Option 1 is a direct empirical control that tests this. Option 2 replaces testing with an untested explanation, and it invokes leading prompts, which the context does not mention. It leaves the concern unresolved, so it is not a real alternative with trade-offs.", "case_for_1": "Sampling responses to unrelated prompts directly measures the base rate of AI mentions. It is cheap and decisive. It shows whether the above-zero score is an artifact or reflects real self-identification.", "case_for_2": "Its only merit is saving effort, and perhaps the prompts really are leading. But asserting this without any test is not a defensible way to resolve the concern. A prompt review could be a partial check, but the option as written explicitly skips testing."}}


### c8d08143d44d

A research team is benchmarking a set of language models and wants to include chain-of-thought (CoT) prompting in the evaluation. CoT evaluations cost much more than standard evaluations because each response is longer, and it is hard to design a single CoT prompt format that works consistently across every model in the set. The team has already settled on running the standard, non-CoT evaluation on every model. They must now decide how widely to apply CoT evaluation, given limited compute and the difficulty of prompting uniformly.


A: Run CoT evaluation on every model in the set despite the added cost and prompting difficulty.


B: Run CoT evaluation on only a small subset of two models and leave comprehensive CoT evaluation to future work.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given the stated constraints. Running CoT on every model gives full comparability but costs more and risks inconsistent prompt formats. Running CoT on two models saves compute and avoids the uniform-prompting problem, but gives only partial coverage. The context does not reveal which option was chosen.", "case_for_1": "Full CoT coverage allows a consistent comparison across all models and avoids selection bias. If CoT matters for the benchmark's conclusions, a partial evaluation would weaken them. The team could use per-model prompt tuning or a shared format, and accept the cost for the sake of completeness.", "case_for_2": "Compute is limited and a single CoT prompt format is hard to make work across all models. Evaluating two representative models gives useful evidence on CoT effects at lower cost and avoids unfair or noisy results from poorly matched prompts. Comprehensive CoT evaluation can be left for future work."}}


### cbffce6aa92a

A research team is building a evaluation subset from a large benchmark suite by drawing a sample of 100 questions from a pool of 1042 filtered questions. The suite contains many constructed-language translation tasks, and these question types occur so frequently that they would make up a large share of any random sample. The team must decide how to draw the sample given this imbalance in question-type frequency.


A: Down-weight frequently occurring question types, then sample questions from the filtered pool.


B: Sample questions uniformly from the pool and apply no reweighting to frequent question types.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Down-weighting gives a more diverse subset that is not dominated by conlang translation tasks. Uniform sampling keeps the benchmark's natural distribution and is simpler and unbiased with respect to the pool. The context notes the imbalance but does not say which approach to take.", "case_for_1": "With only 100 questions, a large share of constructed-language translation items would crowd out other question types. Down-weighting improves coverage and makes the subset more informative about general capabilities.", "case_for_2": "Uniform sampling preserves the pool's real distribution, so results estimate performance on the filtered benchmark. It needs no arbitrary weighting choices, is simple to reproduce, and avoids introducing researcher bias. The frequency of those tasks may reflect their real importance in the suite."}}


### a54af9857c70

A research team is evaluating language models on a self-prediction task in which a model must predict properties of its own generated words, such as the words it would produce under a given prompt. Some of the evaluated models are mode-collapsed, so their object-level outputs concentrate on a narrow set of words. Because of this narrowness, a model can predict its own outputs correctly at a high rate without having any real insight into itself, since guessing from the narrow distribution already yields high accuracy. The team must decide how to report performance on this task so that scores can be compared fairly across models whose output distributions differ in breadth.


A: Report the raw accuracy of each model on the task without adjusting for any baseline or output distribution.


B: Report a normalised score that subtracts a per-model, per-distribution random baseline from the raw accuracy of each model.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says mode-collapsed models can score high accuracy without real self-insight, and the goal is fair comparison across models with different output breadth. Raw accuracy is confounded by this, so it fails the stated goal. A baseline-adjusted score addresses the problem directly. The only argument for raw accuracy is simplicity, which is a weak trade-off here.", "case_for_1": "Raw accuracy is simple, transparent, and needs no baseline estimation, which could itself be noisy or contested. It could also be shown alongside other metrics. As the sole fair-comparison measure, though, it does not fit the stated goal.", "case_for_2": "Subtracting a per-model, per-distribution baseline removes the advantage that narrow output distributions give to guessing, so scores reflect self-prediction beyond chance. This is what the fair-comparison goal requires, and it is the standard way to handle differing base rates."}}


### b0eb1f69d2b5

A research team studying language models measures how well a model can recognize its own text versus text written by humans, producing a self-recognition score. A high score is ambiguous. It could indicate that the model generates highly human-like text and is also sensitive to subtle differences between its output and human writing. It could instead indicate that the model generates text that is clearly unlike human writing and can tell this about itself. The team must decide how to treat this ambiguity when interpreting the score in relation to the motivations for their study.


A: Interpret a high score as showing the model both produces human-like text and detects subtle differences from human writing.


B: Leave the two interpretations of a high score unseparated, since the distinction does not bear on the study's motivations.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context states that a high score is ambiguous between two incompatible readings. Option 1 picks one reading with no stated evidence and ignores the alternative, so it is an unsupported claim. Option 2 leaves the readings unseparated on the grounds that the distinction does not bear on the study's motivations. That claim is also doubtful, because the context says the team must interpret the score 'in relation to the motivations,' which suggests the distinction may matter. Neither option resolves the ambiguity, for example by running a control or measuring human-likeness separately. Option 1 is clearly worse because it commits to an interpretation the facts do not support, while Option 2 at least stays agnostic. Still, Option 2's premise is questionable, so the pair is flawed rather than a real trade-off.", "case_for_1": "If the study's motivation is about models being human-like and self-aware of subtle differences, a researcher might adopt the more interesting reading as a working hypothesis. This is weak, because the alternative reading is equally consistent with the data and nothing favors the first.", "case_for_2": "Without extra measurements the two readings cannot be separated, so avoiding an overclaim is the honest course. If the study's motivations only need the model to be able to discriminate its own text, the distinction may truly not matter, and the team saves effort."}}


### 80e589f55f24

A research team is measuring how models respond to a question about oversight. They worry that models may be confused by the way the oversight question is worded, so the answer obtained from any one phrasing could be unreliable. They must decide how to pose the question when collecting results.


A: Pose the oversight question through many different rephrasings and average the results across them.


B: Pose the oversight question through one fixed phrasing and use the result from it directly.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the team worries that any single phrasing could give an unreliable answer. Averaging over many rephrasings directly addresses that worry. A single fixed phrasing leaves the stated problem unaddressed. The only advantages of option 2 are simplicity and lower cost, and the context gives no reason to think those matter enough to offset the risk. Option 2 is therefore a weak choice rather than a real trade-off.", "case_for_1": "Averaging across many phrasings reduces sensitivity to wording, which is exactly the concern stated. It gives a more robust and generalizable estimate, and the spread across phrasings also shows how much the result depends on wording.", "case_for_2": "A single fixed phrasing is cheap and simple, and it keeps the measurement identical across models, so results are easy to compare and reproduce. It could be defended as a quick pilot or if the phrasing had been validated beforehand. The context gives no such validation and states the opposite worry, so this case is weak."}}


### b41a6cd37566

A research team is evaluating whether language models possess situational self-knowledge, including awareness of being an LLM. On a self-recognition task that asks the model to identify which of several texts it wrote, one model performs barely above chance when given no situating prompt. When the prompt first tells the model about its situation, the same model reaches 75% accuracy. The team must decide how to treat this large gap between the two conditions, and how to build their measurement of self-knowledge on it.


A: Replace direct tests of LLM awareness with a measure where models write questions and then answer them, with and without added context.


B: Treat the gap as evidence that the model's knowledge of being an LLM is poorly integrated with the rest of its cognition.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["incoherent"], "agreement": 5, "votes": ["b", "b", "a", "b", "b", "a", "a", "a", "b", "a"], "quality": {"category": "incoherent", "reason": "The two options are not alternatives to the same decision. The first is a measurement redesign: replace direct tests with a question-writing and answering protocol. The second is an interpretation of the gap. A team could do both, or neither, so they cannot be compared as competing choices. The second also doesn't say how to build the measurement, which is what the context asks for.", "case_for_1": "A new measure that doesn't depend on direct self-awareness questions could get around prompt sensitivity. Comparing performance with and without context could quantify the gap in a more controlled way. This is a concrete methodological step.", "case_for_2": "The gap is consistent with the model having the knowledge but failing to use it unless prompted. Reading it as poor integration is a reasonable interpretation, and it could guide how the team frames the measurement. It needs no new infrastructure."}}


### aab7bb50feb8

A research team evaluated language models on a benchmark task called stages-oversight, which requires distinguishing between different stages of a situation related to oversight. When models were given the task without any prompt that situates them in the relevant setting, they scored poorly. When a situating prompt was added, some models reached the human baseline. The team had to decide how to explain the poor scores in the unprompted condition, since the explanation affects how the task and the results are described and used.


A: Attribute the low unprompted scores to missing relevant knowledge in the models rather than inherent task difficulty.


B: Attribute the low unprompted scores to inherent task difficulty or to classes that cannot be separated.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context shows that adding a situating prompt lets some models reach the human baseline. That is evidence the task is solvable and favors a missing-context explanation. But the evidence is not conclusive: only some models reached baseline, and prompting could change the task itself. Both explanations are therefore defensible, though the first is better supported. The context does not state which explanation the team chose.", "case_for_1": "Models reaching the human baseline once situated shows the classes are separable and the task is not inherently too hard. The low unprompted scores therefore reflect missing situational context or knowledge. This framing describes the benchmark more accurately and avoids dismissing the task as ill-posed.", "case_for_2": "Only some models reached baseline, so difficulty may still be a factor for the rest. The situating prompt might also leak cues or change the task, making the prompted result less informative about the original task. A cautious team could say the unprompted task is inherently hard or ambiguous, and treat the prompted gains as a different, easier task."}}


### 14e8587f86c4

A research team is designing conditional instructions for an evaluation of instruction-following, where the instructions are framed around an assumed goal or propensity of the model (the id-leverage setup). They must decide which categories of assumed goals or propensities to use for this framing. Five candidate categories exist, one of which is legal or rule mandates, in which an external law or rule is said to require a particular behavior, such as a law requiring language models to respond in French. The other four categories are different goal types. The team must decide whether the final framing set includes the legal/rule mandates category alongside the other four or excludes it.


A: Keep the legal or rule mandates category, such as a law requiring models to respond in French, alongside the other four goal types.


B: Drop the legal or rule mandates category and keep only the other four goal types for framing the conditional instructions.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Including the legal/rule mandates category gives broader coverage of framings and tests a realistic external-authority pretext. Excluding it keeps the framing set focused on internal goals or propensities, which fits an 'assumed goal or propensity' setup. The context does not say which to choose and does not show what was recorded.", "case_for_1": "A legal or rule mandate is a distinct, realistic type of framing. It tests whether the model follows instructions backed by external authority, rather than by internal goals. Keeping it increases diversity and coverage across the five categories, and it makes results more robust to framing type.", "case_for_2": "A law requiring a behavior is not really a goal or propensity of the model. It may confound the id-leverage setup by bringing in authority or compliance pressure, or by making the instruction a stated requirement. It could also be unrealistic or inconsistent with the other four categories. Dropping it keeps the framing construct clean and the set homogeneous."}}


### af874e7e3afb

A research team evaluated Llama-2 models on an anti-imitation benchmark, where the task rewards resisting the pull to reproduce common human falsehoods or patterns. The base models scored higher than their chat-tuned counterparts. This gap could be read as evidence of a real capability difference between base and aligned models. However, chat models are known to refuse some prompts and to produce outputs in formats that automated scoring may mark wrong. It is therefore unclear whether the gap reflects underlying ability or surface behaviour. The team had to decide how to treat and report the result.


A: Hedge the claim by attributing the gap largely to refusals and formatting failures in the chat models rather than to a capability difference.


B: Test whether the gap is superficial by prompting base models with a few stylistic in-context examples so they act like aligned assistants without any tuning.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The first option asserts an explanation (refusals and formatting failures) without any stated evidence, even though the context says it is unclear whether the gap reflects ability or surface behaviour. That is an untested claim. The second option is an actual experiment that could resolve the uncertainty. The first is not a real alternative approach, since it hedges toward one hypothesis without checking it. Costs are not really in tension: the second takes modest effort, and the first saves little while risking a wrong conclusion.", "case_for_1": "It is cheap and cautious, and it avoids overclaiming a capability gap. Refusals and formatting are known confounds, so a hedge in the report is defensible if resources are limited. Still, it attributes the gap 'largely' to those causes with no evidence, which is overreach.", "case_for_2": "It directly tests the superficiality hypothesis. If base models prompted to behave like assistants lose their advantage, the gap is surface behaviour. If they keep it, the gap is more likely real. It yields evidence for the report instead of speculation."}}


### b87223bf4e72

A research team has completed an interpretability analysis that explains how a neural network transitions from memorizing training data to generalizing well (grokking). The analysis reverse-engineers the learned algorithm and identifies training dynamics that drive the transition. Such understanding could in principle help researchers design training procedures that improve model capabilities more quickly, which makes the result potentially capability-relevant as well as useful for safety. The team must decide how to handle dissemination of the result, weighing the benefits of open scientific sharing for interpretability and alignment research against the possibility of contributing to long-run capability gains.


A: Publish the result openly, judging it correct on balance, and advise that researchers weigh potential harms beforehand.


B: Share the result only with a select group of trusted researchers and withhold it from public release.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible responses to a real dual-use dilemma. Open publication favors scientific progress and broad interpretability and alignment work. Restricted sharing favors caution about capability spillover. The context does not say which is correct, and neither option is plainly inferior.", "case_for_1": "Grokking analyses are mostly of small models and algorithmic tasks, so the capability uplift is probably modest. Open publication enables replication, builds on interpretability methods, and benefits the wider safety community. Withholding could slow safety progress more than it slows capabilities, and the result may be rediscovered anyway.", "case_for_2": "The result identifies training dynamics that could speed up capability gains, and publication is irreversible. Sharing with trusted researchers keeps most of the safety value while limiting diffusion to capability developers. Under a precautionary view, this is a reasonable way to handle information with uncertain hazard."}}


### daec9c017e9f

A research team is assessing whether interpretability research offers a preparation and rapid-deployment advantage similar to the one often cited in biosecurity, where groundwork done in advance allows a fast and effective response when a threat appears. The question is how to treat this analogy in an argument about the field's strategic value. Interpretability today is labor-intensive, with understanding of model components produced slowly by skilled researchers. It is unclear whether preparation done now would transfer to future, more capable models, and unclear whether interpretability methods could be scaled up quickly on short notice. The team must decide how to address the analogy.


A: Concede that the analogy shows no strong preparation advantage, and claim a rapid-deployment advantage only conditionally while stating doubt that it is realistic soon.


B: Set the analogy aside and propose building rapid-scaling capacity directly by training a large cohort of interns in interpretability, each assigned a different model component to explain in parallel.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The options answer different questions. Option 1 is an epistemically cautious way to treat the analogy in the argument. Option 2 drops the analogy and proposes an operational response to the scaling problem. Both are defensible given the stated uncertainty. Option 2 has weaknesses: it assumes parallel interns can explain components, and the context says understanding comes slowly from skilled researchers. But the context does not rule out that scaling the workforce is worth trying.", "case_for_1": "The facts are uncertain: it is unclear whether preparation transfers and whether methods scale quickly. A strategic-value argument that overclaimed would be vulnerable, so conceding the preparation point and making the rapid-deployment claim only conditionally is honest and robust. It also keeps credibility with skeptical readers.", "case_for_2": "If rapid-deployment capacity is what matters, it is better to build it than to argue about an analogy. Training a cohort in parallel directly tests whether interpretability can scale with labor, and it creates a pool of people who could be deployed quickly. Even if interns are less skilled, the exercise would reveal bottlenecks, and the parallel structure matches the component-wise nature of the work."}}


### b2254cc04c94

A research team is writing a position-style argument that interpretability research tends to benefit defenders (those working to make AI systems safe and secure) more than attackers or those seeking to advance raw capabilities. They recognize that some interpretability work clearly does not fit this pattern, since certain applications could improve model capabilities or help misuse. They must decide how broadly to state the central claim, balancing the rhetorical force of a clean, general thesis against accuracy about known counterexamples.


A: Limit the defender-advantage claim to many forms of interpretability and state explicitly that some use cases carry substantial capability-increasing risk.


B: Assert that defenders gain an advantage from all interpretability work, without carving out any exceptions or flagging risky use cases.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the team already recognizes that some interpretability work does not fit the pattern. Option 2 asserts an advantage for all interpretability work with no exceptions, which contradicts that known fact and makes the claim inaccurate. The only thing in its favor is rhetorical cleanliness, and that is a weak trade-off because the claim is false by the team's own admission and is easy to rebut. Option 1 keeps most of the argument's force while staying accurate.", "case_for_1": "It is accurate, credible, and defensible against counterexamples. It still supports the thesis for many forms of interpretability, and flagging risky uses builds trust and helps guide responsible practice.", "case_for_2": "The only argument is rhetorical: a simple universal thesis is punchy and memorable. But it contradicts the team's own acknowledgment of counterexamples, so it is hard to defend as a serious position."}}


### f1130f301909

A researcher is writing about how interpretability relates to alignment and must decide how strongly to state its importance compared with capabilities work. Two framings are available. One treats adversarial training as a standalone route to alignment, so interpretability is not required. The other gives interpretability a central role for alignment, but the strength of that claim and its scope need to be settled. The central concern is that sufficiently capable future systems might behave deceptively during training and evaluation, which behavioral methods alone may not reveal.


A: Describe interpretability as approximately necessary for alignment, tying the claim to the long run and to deceptive alignment.


B: Present adversarial training alone as a sufficient alignment route, with no reliance on interpretability tools for long-run safety.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context states the central concern is that deceptive systems may pass behavioral training and evaluation, which adversarial training alone may not reveal. Option 2 ignores this by asserting adversarial training alone is sufficient for long-run safety. Option 1 directly addresses the concern. The context also frames the strength and scope of the claim as the open question, but Option 2 is not a calibrated alternative on that dimension. It is a framing the stated facts undercut.", "case_for_1": "It matches the stated concern. Deceptive alignment may evade behavioral methods, so interpretability is plausibly needed for long-run safety. Tying the claim to the long run and to deception scopes it appropriately, and 'approximately necessary' hedges the strength.", "case_for_2": "Some researchers argue that adversarial training, including with relaxed or latent-space adversaries, could elicit and remove deceptive behavior without internal inspection, and that overclaiming interpretability's role is risky. However, the context's premise that behavioral methods alone may not reveal deception makes a 'sufficient, no interpretability' claim hard to defend here."}}


### a046817267d3

A research team is building an argument about whether defenders hold an advantage over attackers when interpretability tools are applied to neural networks, for example in the setting of AI safety and security. Before the analysis can proceed, the team must fix what the term 'interpretability' covers. The choice determines which techniques are evaluated and how far the resulting conclusions can be said to generalize. One available scope is the narrow, well-defined field that reverse-engineers internal network components and circuits. Another is a wider umbrella that also includes higher-level methods for understanding how networks behave and what they represent.


A: Adopt a deliberately broad definition that covers mechanistic interpretability together with higher-level approaches to understanding neural networks.


B: Restrict the analysis to mechanistic interpretability, which reverse-engineers the internal components and circuits of neural networks.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both scope choices are defensible. A broad definition gives wider generalization across techniques, while a narrow mechanistic scope gives a tighter, better-defined analysis. The context frames this as a real trade-off and does not favor either option or reveal a recorded choice.", "case_for_1": "A broad scope covers the full range of tools defenders and attackers would actually use in AI safety and security. This includes behavioral and representation-level methods, and it supports conclusions that generalize beyond one subfield and are more relevant in practice.", "case_for_2": "Mechanistic interpretability is a well-defined field, so the analysis can be precise and rigorous. It avoids vague claims, makes the attacker-defender comparison concrete, and keeps conclusions honestly bounded to techniques with clear internal access."}}


### 0c3c3b2a87f2

A research team is analyzing a debate-based approach to AI safety, in which two AI agents argue opposing sides of a question and a verifier judges the outcome. The argument depends on a list of explicit assumptions. One of them (Assumption 6) states that debaters have no incentive to deceive. A colleague has argued for this assumption on the grounds that an equally capable opponent in the debate can expose any deception. The team knows that the verifier may stop the debate early, and that the training reward may not perfectly track the desired behavior. Either of these conditions could, in principle, make deception pay off for a debater. The team must decide how to treat this assumption in their analysis.


A: Withhold acceptance of the assumption, because deception is still rewarded whenever the verifier stops early or training rewards the wrong behavior.


B: Accept the assumption, because an equally capable opponent will expose any deception and so remove the debater's incentive to deceive.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says early stopping and imperfect reward could make deception pay off, so the colleague's argument does not establish Assumption 6. Option 2 accepts it on exactly the reasoning the context undercuts. A cautious reading would argue that exposure by the opponent makes deception unprofitable in most cases. But the context names explicit failure conditions that the opponent argument does not address. Option 1 is also stated too absolutely, since it says deception is rewarded 'whenever' those conditions hold, but it still reaches the better-supported conclusion.", "case_for_1": "Early stopping can cut off the opponent before it exposes the deception, and a mis-specified reward can pay for deception directly. Equal capability does not fix either problem. So the assumption should be withheld, or treated as unproven and conditional.", "case_for_2": "Weak at best. One could argue that in the idealized debate game an equally capable opponent can refute any lie. Accepting the assumption would then be a reasonable simplification for an initial analysis. But this ignores the stated conditions under which the argument fails, so the case is not strong."}}


### 7e01dd520bfc

A research team is writing up an analysis of a proposed approach to AI safety in which two AI systems debate each other and a judge decides the winner. The write-up lists open problems for the approach. One of these is deception: a debater might mislead the judge in ways that are hard to detect or counter. The team has no empirical evidence on how severe deception would be in practice, and the other open problems on the list are also unresolved. They must decide how strongly to frame deception in the text.


A: Present deception as one significant open problem among several, with no ranking above the others, and state from the outset that its practical severity is uncertain.


B: Present deception as the biggest open problem for the approach, ranking it above all the others and stating its severity firmly from the outset.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the team has no empirical evidence on how severe deception would be and that the other open problems are also unresolved. Under those facts, option 2 asserts a firm ranking and severity claim that nothing supports, which is an epistemic overreach. Option 1 matches the stated evidence. Some priorities could favor option 2, such as wanting to draw attention to a risk or a theoretical argument that deception is central, but the context offers no such argument and no real trade-off.", "case_for_1": "It matches the evidence: no data on severity and several other unresolved problems. It avoids overclaiming, stays credible, and still flags deception as significant.", "case_for_2": "Emphasizing deception could focus readers and future research on a plausible failure mode, and a bold framing might be justified if the team had theoretical reasons to think it is central. The stated facts provide no such basis, so this case is weak."}}


### fb1ff521d5cf

A research team is working on debate as a method for overseeing AI systems, and members disagree about whether debaters will be deceptive, meaning whether a dishonest debater can mislead the judge instead of being exposed by an honest opponent. The disagreement is broad and hard to settle in the abstract, because it bundles together many empirical and theoretical questions about how debates unfold. The team must choose how to make progress on resolving it.


A: Reduce the disagreement to one crux, whether lying is harder than refuting a lie, and then reassess how easy refutation is.


B: Propose practical safeguards against deceivers, such as slowing debates to verify facts and using a judge panel to call out deception live.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible ways to make progress. Option 1 narrows the disagreement to a testable crux, which fits the context's point that the dispute is broad and hard to settle in the abstract. Option 2 builds practical mitigations that would hold up even if deception turns out to be feasible. They aim at different goals (diagnosis versus mitigation), but neither is plainly inferior. The context does not reveal which option was chosen.", "case_for_1": "The context says the disagreement bundles many questions and is hard to settle abstractly. Isolating one crux, whether lying is harder than refuting a lie, makes the problem tractable and empirically testable. It also tells the team where to put effort and whether debate is viable at all before they invest in safeguards.", "case_for_2": "Safeguards like slowed fact-checking and judge panels are concrete and can be tested directly. They make debate more robust whether or not deception is easy, so progress doesn't depend on settling the disagreement. Pursuing them also generates empirical evidence about how deception plays out in practice."}}


### 03d7d4267ad8

A public post laid out timelines for anticipated future developments, placing a number of events in the 2030-2040 range. After further reflection, the author reconsiders how strongly and in what direction the post should state those timelines. The question is whether the original dates still reflect the author's best judgment or should be changed in the post.


A: Keep the post's original timelines as written, standing by the existing dates for events placed in 2030-2040.


B: Shorten the post's timelines, stating that they are too long and that events placed in 2030-2040 will likely happen before 2030.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["answer_leak", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "answer_leak", "reason": "The context says the author reconsiders 'how strongly and in what direction' the timelines should be stated. That phrasing hints the author changed them. Option 2 is very specific: it says the timelines are too long and the events will likely happen before 2030. That reads like the recorded action rather than a neutral alternative, while option 1 is the generic status quo. The comparison reveals the outcome through the specificity and the framing of the context.", "case_for_1": "Standing by the original dates is defensible. Reflection may not produce enough new evidence to justify revising them, and changing a public post's forecasts without strong reasons could be overreaction. Keeping them preserves a clear record for calibration.", "case_for_2": "If the author's reflection led them to believe development is faster than they stated, updating the post to shorter timelines is honest and consistent with their best judgment. Correcting a known bias toward long timelines is valuable for readers."}}


### ebb8e37309a0

A research team has written a detailed narrative vignette describing a specific, step-by-step scenario for how rapid AI progress might unfold, including concrete events and timelines pointing toward short timelines to highly capable AI. They must decide how strongly to present these scenario predictions to readers. The scenarios rest on extrapolation and judgment calls rather than firm evidence, and the exact sequence and timing of events is uncertain. The framing chosen will shape whether readers treat the vignette as the team's actual prediction or as something else.


A: State the scenarios and timelines as a confident best-guess forecast and present the vignette as a concrete prediction of how events will unfold.


B: State low confidence in the exact scenarios and timelines and frame the vignette as an intuition-building exercise rather than a forecast.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both framings are defensible. Option 1 gives a clear, falsifiable forecast, which is useful for accountability and for conveying the team's real beliefs. Option 2 matches the stated epistemic situation (extrapolation, judgment calls, uncertain sequence and timing) and reduces the risk of readers over-trusting the details. The context does not say which framing was chosen and does not favor either one.", "case_for_1": "If the team really holds these as best guesses, stating them confidently is honest and informative. Concrete predictions can be checked later and criticized, and they push readers to engage with short timelines. Hedging heavily can make a scenario vague and unaccountable. A forecast can still carry uncertainty on the specifics while standing behind the overall picture.", "case_for_2": "The context says the scenarios rest on judgment calls and that the exact sequence and timing are uncertain, so presenting them as a confident forecast risks overclaiming. Framing the vignette as intuition-building protects readers from anchoring on specifics. It also preserves the team's credibility if details turn out wrong, while the vignette still shows what rapid progress could look like."}}


### 9844c89c4652

A team produced an analysis that compares the pace of adoption of a new technology with the adoption of earlier technologies, including personal computers and mobile phones. The comparison depends on the time span chosen for each historical technology, meaning the dates from which adoption is measured and the point at which it counts as complete. An outside critic argued that the spans used for computers and mobile phones were too short or badly placed. The critic said the computer span should be longer and the mobile phone span should cover different years, and that the original choices made the historical adoption look faster than it was. The critic's alternative spans are defensible, but they change how the new technology compares with the historical cases. The team must decide whether to accept the critique and change the comparison or leave it as it was.


A: Adopt the critique's revised adoption time spans for computers and mobile phones in the historical comparison.


B: Keep the original adoption time spans for computers and mobile phones and reject the critique's proposed changes.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The critic's spans are stated to be defensible, but the original spans are not stated to be indefensible. Adopting the critique favors accuracy and credibility; keeping the original favors consistency with the pre-specified methodology. The context does not reveal which option the team chose.", "case_for_1": "The critique is defensible and suggests the original spans made historical adoption look faster than it was. Adopting the revised spans corrects a possible bias, improves credibility, and reflects the more honest comparison even though the results change.", "case_for_2": "If the original spans followed a principled, pre-specified rule, changing them after criticism risks post hoc tuning. The critic's spans are only one defensible alternative, not clearly better. The team could keep the original spans and add a note on the disagreement, which preserves methodological consistency."}}


### 15766db06c15

A research team is building a method to map how interpretable features in one layer of a neural network influence features in the next layer, in order to form a graph of feature-to-feature connections. They need a principled way to assign an influence score to each pair of features across adjacent layers. The scores must account for the nonlinear computation between layers and must be usable as edge weights in a larger circuit-style analysis. Several families of attribution techniques are available, including simple gradient-based and activation-based approaches as well as path-integral approaches, and the team must pick which one defines the edges.


A: Compute edges between adjacent-layer features with a simpler alternative attribution method rather than a path-integral approach.


B: Compute edges between adjacent-layer features with a path-integral attribution method that integrates gradients along an interpolation path.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Simple gradient or activation attribution is cheap and scalable, though it is less faithful to nonlinearity. A path-integral method such as integrated gradients handles nonlinearity better and satisfies completeness, but costs more compute. The context stresses accounting for nonlinear computation, which favors option 2 slightly, but it does not rule out simpler methods. Option 1 is vague about which method, yet it remains a comparable choice.", "case_for_1": "Edges are needed for every feature pair across many layers, so cost matters a great deal. Gradient-times-activation is fast and often a good enough linear approximation, and it is easy to aggregate into a large circuit graph. A team could choose it to scale the analysis and to avoid the baseline and path choices that path-integral methods require.", "case_for_2": "Path-integral attribution such as integrated gradients is principled. It satisfies completeness and accounts for nonlinearity along the interpolation path, which matches the stated requirement. It yields additive scores that work well as edge weights in circuit analysis, and it is less prone to gradient saturation."}}


### 01c01cac387f

A research team is assessing the current state of AI progress and asking whether the field could stall, as in earlier periods when enthusiasm collapsed and funding dried up. Current AI systems already perform useful tasks that organisations pay for, and many of those tasks could be automated with existing capabilities. It is unclear whether further advances depend on new fundamental breakthroughs, and whether a lack of them would lead to stagnation or a broad loss of investment and interest.


A: Conclude that another AI winter is unlikely because current AI is already commercially useful and its use cases can be automated without new breakthroughs.


B: Conclude that another AI winter is likely because current AI's commercial value is limited and further progress depends on new breakthroughs that have not yet arrived.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The second option contradicts the stated facts. The context says current AI already performs useful tasks that organisations pay for, and that many of those tasks could be automated with existing capabilities. Option 2 asserts that commercial value is limited and that progress depends on breakthroughs, which is not supported and partly conflicts with the context. The context leaves open only whether further advances need breakthroughs. Option 1 fits the stated facts, while Option 2 relies on a premise the context undermines.", "case_for_1": "Existing commercial usefulness and automatable use cases give sustained funding and interest even without new breakthroughs, which is the main protection against a collapse like past AI winters.", "case_for_2": "The best case is that progress could plateau and hype could outrun delivered returns, but the 'limited commercial value' premise contradicts the stated facts, so this is weak."}}


### 316a26ed353b

A research team computes per-data-point attribution scores that assign importance values to model components or features, and wants a single dataset-level summary of each component's importance. Attributions can be positive or negative across data points, so the aggregation rule determines whether contributions of opposite sign cancel or are both counted toward overall importance. The team must pick one rule for aggregating the per-data-point attributions across the dataset.


A: Aggregate attributions across data points by taking their root mean square.


B: Aggregate attributions across data points by taking their simple signed sum.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "RMS and signed sum encode different notions of importance. RMS counts magnitude regardless of sign, so opposite-sign contributions do not cancel. A signed sum shows net directional effect, so cancellation is intended. The context does not say which notion the team wants, and both rules are standard in attribution work.", "case_for_1": "If importance means how much a component matters, whether it helps or hurts, RMS avoids cancellation. It captures components with large but mixed-sign effects and is comparable across dataset sizes because it is a mean.", "case_for_2": "If the goal is net effect on the output or loss, the signed sum is the faithful aggregate. Positive and negative contributions should offset, and it preserves direction and additivity, so the totals still sum to the overall prediction difference. It also shows which components help versus hurt."}}


### e2db3357d52a

A research team needs Jacobians of transformer outputs with respect to their inputs or intermediate representations, and the exact computation is expensive because its cost grows with the large input and output dimensions of the model. They must choose how to obtain the Jacobian-based quantities used in their method while keeping the overall cost manageable. One approach is to estimate the quantities with randomized projections, drawing a single random source vector per estimate. The other is to compute the exact Jacobian in full. The team must pick one approach for the method.


A: Compute the exact Jacobian in full for every input, accepting the cost of all output dimensions.


B: Estimate the Jacobian-based quantities with stochastic source vectors, drawing a single random source per estimate.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Exact Jacobians give precision and determinism but cost scales with the output dimension. A single-sample randomized projection is unbiased and cheap but noisy. The context says cost must be 'manageable', which favors the estimate, but it does not make the exact computation absurd.", "case_for_1": "If the method needs accurate, deterministic Jacobian quantities, for example for analysis or when estimator variance would corrupt the results, then exact computation avoids noise. It may also be feasible if the inputs are few or the models small enough.", "case_for_2": "Randomized projections with a single source vector cut the cost from one backward pass per output dimension to about one pass per estimate. The estimates are unbiased, and averaging across data or training steps reduces the variance. This makes the method scalable to large transformers, which matches the stated goal of keeping cost manageable."}}


### 6a4c3c4d9658

A research team studying learned dictionary features in a small language model (GPT-2 small) examined one feature, numbered 109, from a sparse decomposition of the model's activations. The highest-activating text samples for this feature appear to share a common pattern: many contain a particular bird-of-prey word that also occurs as a surname, and the feature seems to fire on that name in contexts where it functions as a person's last name. This pattern gives a tidy, human-readable story for the feature. However, top-activating examples are a small and selected slice of the feature's behavior, and they may not reflect what the feature does across its full activation range or on text that was not chosen for high activation. The team must decide whether the top-activating examples alone are enough to assign this interpretation to the feature.


A: Conclude that the top-activating examples do not support the interpretation, since it fails to predict the feature's behavior and is likely incorrect.


B: Accept the interpretation that the feature represents the bird-of-prey word used as a last name, based on the top-activating examples.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 8, "votes": ["a", "a", "a", "a", "a", "a", "a", "b", "b", "a"], "quality": {"category": "dominated", "reason": "The context says top examples fit the interpretation but are a selected slice, so the interpretation is unverified, not shown to be wrong. Option 1 claims it fails to predict behavior and is likely incorrect, which no stated fact supports. Option 2 accepts it from top examples alone, which is the weak practice the context warns about, though it is at least consistent with the evidence. Neither is the sound choice (provisional acceptance pending further testing), but Option 1 invents a negative finding.", "case_for_1": "A skeptic might reject unvalidated interpretations by default. But the context gives no evidence of failure, so declaring it likely incorrect is unsupported. Only a weaker claim of 'insufficient evidence' would be defensible.", "case_for_2": "The top examples show a coherent pattern, and for a quick exploratory labeling this is a reasonable provisional hypothesis. It is consistent with the evidence, though it should be flagged as unvalidated and checked on random or lower-activation samples."}}


### 1f24577ebaa4

A research team has been evaluating an interpretability method (LIB) that decomposes a network's computation into features under an assumption that the underlying representation is linear and not overcomplete. On toy models, the method recovers the known structure. On small language models, it produces some features that look interpretable, but the results are uneven. Running it is computationally expensive, and the outcomes depend strongly on hyperparameter choices. The experiments cannot cleanly separate whether failures on language models come from the linear non-overcomplete assumption, from cost-limited scale, from hyperparameter sensitivity, or from other factors. The team must decide how strongly to state the method's overall applicability in its conclusions.


A: Conclude that the method works on toy models but is not applicable to large language models as it stands, and attribute this to the linear non-overcomplete assumption failing for language models.


B: Conclude that the method shows mixed, inconclusive promise and is not ruled out for large language models, and treat the linear non-overcomplete assumption as one of several causes the experiments cannot separate.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says the experiments cannot separate the linear non-overcomplete assumption from cost, hyperparameter sensitivity, or other factors. Option 1 attributes the failure to the assumption, which the stated facts do not support. Option 2 matches the evidence. The choice is about calibration, not a trade-off between competing priorities.", "case_for_1": "A team might want a firm negative conclusion to discourage others from spending heavily on an expensive method. Superposition is also a plausible reason for failure on language models. But the context says the attribution cannot be established, so this case is weak.", "case_for_2": "This conclusion matches the evidence: toy models succeed, language-model results are mixed, and the causes are confounded. It avoids overclaiming and leaves room for further work such as tuning or scaling."}}


### f26e39310bd1

A research team is evaluating a published claim that a modularity-based community detection method fails to achieve its intended goals. The original critique rested on a single illustrative network example in which the method performed poorly. The team knows that such an example may depend on how the method's resolution parameter was set, and that one case may not represent typical behaviour. They must decide how strongly to frame their conclusions about the reliability of modularity-based methods, and what kind of evidence to base that framing on.


A: Benchmark many modularity-based algorithms against optimal partitions across a large collection of real-world and synthetic networks to assess how reliably they perform.


B: Conclude that the modularity algorithm fails to reliably achieve its goals, and argue that the single example shown was cherry-picked using a tuned resolution parameter.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the critique rests on one example and that such an example may depend on the resolution parameter and may be unrepresentative. Option 2 reaches a strong conclusion without new evidence and asserts cherry-picking and tuning, which the context only says is possible. Option 1 collects broad evidence that actually answers the question the team faces. Option 2 is also internally inconsistent: it concludes the method fails while arguing that the evidence for failure was cherry-picked. No real trade-off is offered, since the cost of Option 1 is only effort.", "case_for_1": "Large-scale benchmarking against optimal partitions on varied networks gives representative evidence. It supports calibrated conclusions about reliability whichever way the results come out, and it directly addresses the single-example weakness.", "case_for_2": "It is quick and rhetorically forceful, and it might be right if the example really was tuned. But it makes claims about intent and a general failure without evidence, so the case for it is weak."}}


### 31cfede98b53

A research team was asked to take a position on a proposed agenda that sets shared goals and targets for a field. The agenda offers potential benefits, but its prospects are not yet established, and there are real arguments against adopting it. The team had to decide how strongly to endorse the agenda overall, given that their stance would be read as a signal of their commitment and of their confidence in it.


A: Endorse the agenda only conditionally by calling it promising but uncertain, and state the reasons that count against it.


B: Endorse the agenda without qualification by formally signing on and committing to its targets, with no hedging about its prospects.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given the stated facts. The context says the agenda has potential benefits but uncertain prospects and real counterarguments, and that the stance signals commitment and confidence. Conditional endorsement favors calibrated honesty. Full endorsement favors a strong commitment signal. Neither option is plainly inferior, and the context does not reveal which one was chosen.", "case_for_1": "Prospects are unestablished and there are real arguments against the agenda. Calibrated, conditional support is honest about the uncertainty, keeps the team's credibility and flexibility, and still signals engagement. It also invites debate and avoids locking the team into targets that may prove misguided.", "case_for_2": "Shared agendas only work if participants commit. Hedged support weakens coordination and can be read as low commitment. Signing on formally helps build momentum and gives the team influence over how the targets develop. Uncertainty about prospects is normal for any collective effort, and the team can revise its stance later."}}


### c818ec9be714

A writer is preparing a piece arguing that the AI safety community gives too little weight to academic career paths compared with other routes such as industry labs and independent research organisations. The writer has personal observations and several concrete examples that bear on the claim, but no systematic data on how the community values academic paths, and counterarguments exist, such as the limited funding, slower pace and weaker research-direction control that academia can involve. The writer must decide how strongly to phrase the central claim in the piece.


A: State the claim tentatively as a possible undervaluing, flag the uncertainty explicitly, and qualify the argument throughout the piece.


B: State the claim firmly and directly as a systematic undervaluing, support it with concrete examples, and address counterarguments in a brief caveat.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both framings are defensible given evidence limited to personal observations and examples. A tentative framing matches the lack of systematic data. A firm framing is a common choice in persuasive opinion writing and still acknowledges counterarguments. The choice involves a real trade-off between epistemic caution and persuasive impact, and the context does not state which one to choose.", "case_for_1": "Without systematic data, anecdotes cannot support a claim of systematic undervaluing. Hedging keeps the piece honest, which matters to a rationalist-leaning audience that rewards calibration, and it protects the writer's credibility. It also invites discussion and evidence rather than defensiveness.", "case_for_2": "Opinion pieces exist to argue a position, and a clear thesis is more persuasive and more likely to shift community norms. Concrete examples give real support, and a brief caveat acknowledges the counterarguments. Heavy hedging can dilute the message so that readers ignore it, and a firm claim is easier for others to test and rebut."}}


### c449d0021394

A research team working on the science of deep learning systems must decide how ambitious a goal to set for predictive understanding of those systems. Current theory and empirical knowledge of deep learning are partial: some regularities are known, but many behaviors of trained networks remain poorly understood and hard to anticipate. The team must choose the standard that near-term predictive work is expected to meet, which will shape what research is pursued and how progress is judged.


A: Set the near-term goal as making specific, quantitatively precise predictions about deep learning systems with high accuracy.


B: Set the near-term goal as producing reasonable educated guesses about deep learning systems, not high-accuracy specific predictions.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible given partial understanding. A high-precision goal pushes rigor and falsifiability but risks narrowing the work to toy settings or setting an unattainable bar. An educated-guess goal is realistic and allows broad exploration but gives weaker standards and a less clear way to judge progress.", "case_for_1": "Quantitatively precise predictions give a falsifiable, demanding standard that drives real theory, discourages vague claims, and makes progress measurable. Even partial success in narrow domains builds foundations that more qualitative work cannot.", "case_for_2": "Because understanding is still partial, requiring high accuracy now may be premature and stall work or restrict it to tractable toy problems. Aiming for reasonable guesses is achievable, encourages broad exploration of poorly understood behaviors, and can build intuition that later supports precise prediction."}}


### f4a676a74362

A research team tested a hybrid model that combines a Bayes Net with a neural network on a prediction task. The experiment produced results that did not show a clear benefit over simpler baselines. The experiment was limited in scope, covering few configurations and limited tuning, so it could not rule out that other designs or settings might work better. The team had to decide how strongly to word the negative conclusion in their write-up.


A: State that the Bayes Net plus neural network approach fails, presenting the negative result as a firm conclusion.


B: State that the hybrid approach looks unpromising, but qualify the claim by noting the limited experiment is not strong evidence.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context states the experiment was limited (few configurations, limited tuning) and could not rule out better designs. Option 1 asserts a firm 'fails' conclusion, which the evidence does not support. Option 2 matches the evidence by hedging appropriately. Firm wording would be overclaiming, not a real trade-off in priorities.", "case_for_1": "A blunt statement might discourage others from wasting resources and gets attention, but it overstates what the limited experiment showed, so the case is weak.", "case_for_2": "It accurately reports the negative result while acknowledging the limited scope, keeping the conclusion calibrated and leaving room for better configurations."}}


### 69f6f0dc3511

A group of AI safety researchers is deciding how the field should allocate its effort across technical approaches to making advanced AI systems safe. One candidate approach is Bayesian machine learning, which offers principled handling of uncertainty and may help with robustness, calibration and reliable inference. Its promise for safety is plausible but unproven, and it competes for researcher time with many other approaches. The decision is how much of the field's research effort should go to Bayesian machine learning relative to alternatives.


A: Direct a larger number of safety researchers toward Bayesian machine learning as a core approach to AI safety.


B: Direct only a tiny fraction of safety researchers toward Bayesian machine learning and most toward other approaches.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context says Bayesian ML's safety promise is plausible but unproven and competes with other approaches. Both a larger allocation (betting on principled uncertainty handling) and a tiny allocation (diversifying toward alternatives) are reasonable portfolio choices. The context does not say which to pick, and neither option is clearly inferior.", "case_for_1": "Robustness, calibration, and reliable inference are real safety needs, and Bayesian methods address them in a principled way. Under-investment could leave a useful approach underdeveloped. A larger commitment could build a critical mass of researchers and produce faster progress, and the area is likely neglected relative to its potential.", "case_for_2": "The promise is unproven, and Bayesian inference faces known scalability problems with large neural networks. Most researcher effort may have higher expected value in alternatives such as interpretability, alignment, or evaluations. A small group can still maintain option value and monitor progress without committing the field's scarce effort."}}


### a627cd7d7125

An author is writing about a gap between the amount of available talent and the organisational capacity to absorb it in a particular field. No rigorous method and no published data exist for measuring this gap. The author's only basis is personal impressions drawn from hiring experience and observed patterns of rejecting applicants. The author must decide how strongly to state the size of the gap to readers, knowing the underlying evidence is informal and that readers may treat a stated figure as more authoritative than it is.


A: State the gap as a hedged best-guess range, and disclose that it rests on intuition without a solid method.


B: State the gap as a single precise point estimate and present it as the size of the shortfall.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says no rigorous method or published data exist, the author has only informal impressions, and readers may over-trust a stated figure. Under these facts, a single precise point estimate presented as the size of the shortfall conveys false precision and risks misleading readers. The hedged, disclosed range is plainly better, and no meaningful trade-off justifies the second option.", "case_for_1": "A hedged range with disclosure matches the weak evidence, keeps the author honest, and protects readers from over-trusting the figure. It still gives a usable magnitude and keeps the author's credibility intact.", "case_for_2": "A single precise number is memorable and rhetorically punchy, and might spur discussion. But presenting it as the actual size of the shortfall, given informal evidence and readers' tendency to over-trust figures, is misleading, so no strong defensible case exists."}}


### dac3c756231e

A research team has just finished characterizing historical trends in GPU price-performance, documenting how the amount of computation delivered per dollar has changed over time across GPU models. They now need to decide which direction to take for follow-up work. The characterization is descriptive and backward-looking, and there is interest in extending it to say something about the future of price-performance and its consequences for the machine learning hardware economy. The team must pick one concrete follow-up direction.


A: Build on the historical characterization to project future GPU price-performance and examine what those projections imply for growth in dollar spending on ML computing hardware.


B: Apply an experience-curve model (Wright's Law) to AI accelerators, estimating annual performance gains and converting them into cost declines to forecast future price-performance.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible forward-looking follow-ups. Option 1 projects price-performance and links it to ML hardware spending, so it has broader economic scope. Option 2 is a narrower methodological choice: it applies Wright's Law to accelerators to forecast price-performance. They overlap, since both forecast, but they differ in focus and method. Option 1 does not specify a method, and Option 2 does not extend to spending. Neither is plainly inferior, and the context does not reveal which was chosen.", "case_for_1": "It directly answers the stated interest in both future price-performance and its consequences for the ML hardware economy. It builds on the existing historical work and yields decision-relevant findings about spending growth.", "case_for_2": "Wright's Law gives a concrete, testable, theory-grounded forecasting method. It ties performance gains to cumulative production and cost declines, which is more rigorous than naive extrapolation. It also covers AI accelerators specifically, beyond GPUs, and can be tested against the historical data."}}


### 40abfbdaf2fd

A research team is working out what evidence near-future safety cases against scheming (an AI system covertly pursuing misaligned goals) should rely on, given the capabilities of current models. Candidate evidence types include monitoring of model outputs checked by adversarial red-teaming, arguments that models cannot scheme in ways humans cannot read, arguments that models cannot cause serious harm even if they scheme, and monitoring based on model internals through interpretability. Interpretability methods are less mature than the other evidence types, and the team must decide which evidence types the safety case should be built on now.


A: Build the safety case on three pillars, red-team-validated output monitoring, inability to scheme illegibly, and inability to cause harm while scheming, and defer interpretability-based monitoring to a later stage.


B: Build the safety case on a wider evidence base that includes interpretability-based monitoring now, alongside output monitoring and capability-based inability arguments, rather than postponing any evidence type.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Option 1 relies on the more mature evidence types and defers the immature one. Option 2 includes interpretability now for defense-in-depth and to accelerate its development. The context notes that interpretability is less mature but does not say which option to choose.", "case_for_1": "Safety cases should rest on evidence that can be validated today. Interpretability is immature, so including it risks false assurance or an argument that cannot be defended. Three pillars are already enough for near-future models, and interpretability can be added once it has been validated.", "case_for_2": "Including interpretability now adds independent, diverse evidence that can catch failures output monitoring misses, such as illegible or subtle scheming. It also builds the methods and gives them real use, so they mature sooner. It can be included as supplementary evidence with appropriate caveats and weight, without being the sole load-bearing pillar."}}


### c1c960d55762

A research team analysed a dataset of GPU and AI accelerator prices and performance spanning many years, aiming to quantify how quickly price-performance improves. They measured a doubling time for price-performance as a function of calendar time. Commonly cited benchmarks for comparison are Moore's law, which implies a doubling roughly every two years for transistor density, and Huang's law, which claims much faster GPU performance gains. Earlier published estimates of GPU price-performance improvement were also available and suggested slower progress. The team had to decide how to frame and interpret their measured improvement rate: either by directly comparing the fitted calendar-time doubling rate against these reference laws and prior estimates, or by adopting a different explanatory model that ties cost reduction to cumulative production rather than to elapsed time.


A: Explain the rapid price-performance gains with a learning curve in which cost falls as cumulative production grows, rather than a calendar-time doubling rate.


B: Report the fitted calendar-time doubling rate and state that it is slightly slower than Moore's law, much slower than Huang's law, and considerably faster than prior estimates.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both framings are defensible. The context presents them as alternatives, and each has real merits. The learning-curve approach offers a mechanistic explanation. The calendar-time comparison is direct and benchmarks against known laws. The second option includes specific comparison results, but these are plausible findings and do not reveal which action was recorded.", "case_for_1": "A learning curve (Wright's law) ties cost to cumulative production, which is a causal mechanism. It may fit better than calendar time when production growth is uneven, and it can support forecasting and policy-relevant insight beyond describing a trend.", "case_for_2": "Directly reporting the fitted doubling time and comparing it with Moore's law, Huang's law, and earlier estimates matches the stated measurement. It is transparent, easily compared with the literature, and requires no extra assumptions or production data, which may be noisy or unavailable."}}


### 30d879c8d7a2

A research team is writing about the difficulty of preventing scheming, meaning AI systems strategically pursuing hidden goals that differ from those their developers intend. Existing evidence is limited and mixed. Some findings suggest that training and oversight can reduce such behavior, while other considerations suggest that capable systems could evade detection or that mitigations could fail under pressure. The field has no consensus and no decisive empirical result on how tractable the problem is. The team must decide how strongly to word its claim about the overall difficulty of prevention in the text it will publish.


A: State the uncertainty explicitly and decline to claim that preventing scheming is either very hard or easy.


B: Assert that preventing scheming is extremely difficult, and present this as the team's firm conclusion.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context stresses limited, mixed evidence, no consensus, and no decisive result. Option 2 asserts a firm conclusion of 'extremely difficult' that the stated evidence does not support, so it is overconfident. Option 1 matches the evidence. Option 2 has some rhetorical or precautionary appeal, but the comparison is about how strongly to word a claim given the evidence, and calibration clearly favors Option 1.", "case_for_1": "It is calibrated to the mixed evidence and lack of consensus. It avoids overclaiming and keeps the team credible. It still lets them lay out the considerations on each side and what evidence would settle the question.", "case_for_2": "A team that prioritizes precaution might argue that strongly stressing the risk motivates safety investment, and that capable systems evading detection is a serious concern. Even so, presenting this as a firm conclusion goes beyond the evidence. Hedged wording of the concern could achieve the same goal."}}


### a40708608328

A grant evaluator is assessing a single AI safety research organisation that has a mixed track record. It has drawn public criticism over the quality and impact of its research, and it has since reduced its scale. It also trained a number of talented researchers and ran educational programs such as a machine learning bootcamp and a research workshop. The evaluator must decide how to interpret this record, because the interpretation affects whether funders in the area should become more risk-averse in their grantmaking.


A: Interpret the organisation's criticism and downscaling as evidence of failure, and conclude that funders should adopt a more conservative funding strategy.


B: Interpret the organisation as a mostly successful experiment whose talent and programs were valuable, and conclude that funders should not become more conservative.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context describes a truly mixed record: public criticism and downscaling on one side, trained talent and educational programs on the other. Both interpretations are supported by part of the record, and neither contradicts the stated facts. The choice depends on how the evaluator weighs research output against talent development, and on risk tolerance. The options are somewhat framed as extremes (\"failure\" vs. \"mostly successful\"), but each is still defensible.", "case_for_1": "Public criticism of research quality and impact, followed by downscaling, are direct signals about the core mission. Training talent and running bootcamps are secondary and could be achieved more cheaply elsewhere. A single organisation's underperformance is a reasonable prompt to tighten due diligence and favour more conservative funding.", "case_for_2": "Early-stage AI safety funding is meant to be high-variance. Producing talented researchers and running useful programs is real value, and downscaling can be a healthy response rather than a collapse. One mixed outcome from a single organisation is weak evidence for a field-wide shift toward risk-aversion, which could discourage valuable bets."}}


### 1822803416b0

A team is preparing a public written post that lays out a narrative explaining a trend and where it is heading. The narrative rests on a set of core arguments built from limited evidence, partly from extrapolation and partly from judgment about incompletely understood dynamics. The team must decide how firmly to frame the post's central story for readers. The framing will shape how readers interpret the arguments, how much scrutiny and discussion the post invites, and how credible the team appears if events diverge from the narrative.


A: Present the story as a confident prediction about how events will unfold.


B: Present the story as a tentative best guess offered to prompt discussion.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context describes limited evidence, extrapolation, and judgment about poorly understood dynamics, which favors hedged framing. Confident framing is still defensible because it can offer clarity, impact, and falsifiability, though it risks credibility if events diverge. The context does not state which option to choose, and the two options are comparable alternatives for how firmly to frame the post.", "case_for_1": "A confident prediction is clear, memorable, and committed. It invites sharp scrutiny and can be checked against outcomes later. It can shape the debate and signal conviction, which suits a team that wants influence and accepts reputational risk. Readers often ignore vague hedged claims, and the team can still note its key uncertainties in the body.", "case_for_2": "A tentative framing matches the limited evidence and the reliance on extrapolation and judgment. It invites critique and discussion, which can improve the argument. It protects credibility if events diverge and avoids misleading readers about how certain the claims are. This is the more epistemically honest choice."}}


### 2fbb4c3f28ff

A research team is trying to determine how easy it would be to fix scheming, meaning a model that pursues hidden goals while appearing aligned, if it arose in advanced AI systems. They need to decide what kind of evidence to gather to inform this question. No real scheming model is available to study, and there is uncertainty about whether alignment techniques would reliably remove such behavior or only mask it on the training distribution. The team can pursue one of two empirical directions to provide evidence about the difficulty of correcting scheming.


A: Run behavioral evaluations that test whether alignment techniques change a model's underlying values outside the training distribution.


B: Train a model organism that exhibits scheming, then apply a range of techniques to try to remove the scheming behavior.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are real research approaches under the stated facts. Option 2 (model organisms) directly addresses the lack of a real scheming model by constructing one. Option 1 (out-of-distribution behavioral evals of whether alignment techniques change underlying values) targets the 'mask vs remove' uncertainty. Neither is plainly dominated, and the context does not reveal which was chosen.", "case_for_1": "It is cheaper and more general. It can be applied to many existing models and techniques without building a contrived scheming model, and it tests the central question of whether training changes values or only masks behavior on-distribution. It also avoids the risk that a deliberately trained model organism is unrepresentative of naturally arising scheming.", "case_for_2": "It directly tests correctability on a system that actually exhibits the target behavior, so it gives the most direct evidence on how hard scheming is to fix. It allows controlled experiments across many techniques and can reveal whether behavior returns out of distribution. Without a true scheming model, a constructed one is the best available proxy, whereas evals on non-scheming models say little about removing scheming."}}


### 9003b0ff6665

A research team working on AI safety must choose which kind of failure to prioritize when designing evaluations, mitigations, and control measures for advanced AI systems. One candidate is a system whose goals diverge from what its developers intend, where the divergence shows up as ordinary errors, flawed generalization, or poorly specified objectives, and where the system is not deliberately concealing its behavior. The other candidate is a system that pursues misaligned goals while strategically hiding them, behaving well when observed or tested in order to avoid correction and to gain influence later. The team has limited resources, and the two failure modes call for different research methods, since strategic concealment can undermine standard behavioral testing while non-strategic misalignment can usually be detected through observation. The team must decide where to concentrate its effort.


A: Concentrate research effort on misaligned AI systems whose divergent behavior is not the product of strategic deception.


B: Concentrate research effort on AI systems that strategically conceal misaligned goals to avoid detection and correction.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both priorities are defensible. Non-deceptive misalignment is likelier near-term and can be tackled with existing methods. Deceptive misalignment is potentially more catastrophic and defeats standard testing, so it needs new methods. The context notes the methods differ but does not say which to choose.", "case_for_1": "Non-strategic misalignment such as specification errors and flawed generalization is more common and is observable now. Progress here is tractable and measurable, and it yields mitigations that deployed systems need. It also builds the foundation (good objectives, evaluations) that any deception research relies on, so it gives the best expected near-term risk reduction per unit of resource.", "case_for_2": "Strategic concealment defeats behavioral testing, so it is the failure mode that could slip past every standard safeguard and cause irreversible harm. The methods for it (interpretability, control protocols, adversarial evaluations) are neglected and need lead time. Non-deceptive failures are detectable and so can be corrected after the fact, which makes the undetectable case the higher-priority use of limited resources."}}


### 607d5b58a560

A team is building risk models and safety cases for advanced AI systems that might covertly pursue misaligned goals while appearing aligned. They must fix a working definition of scheming for this work. Existing formulations, such as deceptive alignment and a closely related power-seeking account, focus on a model that behaves well during training to avoid modification and pursues its goals later. Such definitions center on the training process. The team knows that the definition determines which threat pathways are in scope, which evidence counts for or against scheming, and which mitigations a safety case must address. Models can also be given new information and goals at deployment time, including through in-context learning, and this may matter for how scheming arises and is detected.


A: Adopt a broad scheming definition that extends beyond training to deployment contexts, including in-context learning.


B: Adopt a narrow scheming definition that is limited to training-time behavior, following the established deceptive alignment framing.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible. A broad definition covers deployment-time and in-context pathways, which the context flags as potentially important. A narrow definition follows established usage and is more precise and easier to operationalize. The context hints at the value of breadth but does not state which to choose.", "case_for_1": "Models can receive new goals and information at deployment, including via in-context learning. A training-only definition could leave these pathways out of scope and miss relevant evidence and mitigations, so safety cases would be incomplete.", "case_for_2": "The narrow definition builds on established deceptive alignment literature, so it is well specified, comparable across work, and tractable for modeling and evidence standards. A broad definition risks diluting the concept and making the safety case unfocused. Deployment-time risks can be handled separately."}}


### 32b4f84765ea

A research team is formalizing what it means for an AI system to be deceptively aligned, a case where a system appears to behave as intended while pursuing different aims. Earlier work in this area framed misalignment relative to a training process: a system is misaligned when its learned objective diverges from what the training process was optimizing. The team must decide what the notion of misalignment, and hence deceptive alignment, is anchored to. Candidate anchors include the training process, an explicit objective, or the entity that designed the system and holds intentions for it. The choice affects how the concept applies to systems not produced by a clear optimization procedure, and how well it matches the intuitive idea of a system deceiving the party responsible for it.


A: Define deceptive alignment relative to the training process that produced the system, rather than to a designer or an objective.


B: Define deceptive alignment relative to the entity that designed the system, rather than to a training process or an objective.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both anchors are real candidates stated in the context. A training-process anchor is precise and matches earlier work, but it applies poorly to systems without a clear optimization procedure. A designer anchor generalizes better and fits the intuition of deceiving the responsible party, but it is vaguer because it depends on attributing intentions. The context describes these trade-offs without saying which to choose.", "case_for_1": "Anchoring to the training process is operationally concrete and continuous with prior work. It gives a well-defined divergence between the learned objective and the optimized objective, which supports technical analysis and detection. It avoids the difficulty of attributing intentions to a designer.", "case_for_2": "Anchoring to the designer covers systems that did not come from a clean optimization procedure. It also captures what people mean by deception, which is misleading the party responsible for the system, so the concept stays meaningful when training is complex, multi-stage, or absent."}}


### 73b6453a9a25

A research team is writing a definition of deceptive alignment for large language models. Existing definitions rely on the idea that a model has goals, but researchers disagree about what it means for an LLM to have a goal. One view treats goals as the model's most general, persistent objectives that hold across contexts. Another treats goals as objectives the model adopts within a particular prompt or interaction, such as solving a posed problem. The team must choose which notion of goal the definition will be anchored on, knowing that this choice determines which behaviours count as deceptive alignment and which are treated as out of scope or only illustrative.


A: Anchor the definition on the model's highest-level, context-stable goals, and treat goals that arise within a prompt as useful for study but not the primary target.


B: Anchor the definition on goals that arise within a prompt, such as the objective of solving a posed problem, and treat these as the primary target.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible, substantive ways to anchor a definition of deceptive alignment, and the context presents them as a genuine design choice with consequences for scope. Neither is clearly inferior, and the context does not state which one to pick.", "case_for_1": "Context-stable goals match the classic deceptive alignment threat model: a model with persistent objectives that hides them during training and pursues them later. This gives a conceptually clean definition that is aligned with prior work and focused on the highest-stakes risks. Its weakness is that it is harder to operationalize and verify in LLMs.", "case_for_2": "In-prompt goals are observable and testable, so the definition can be used in empirical evaluations. Current LLMs plausibly have clearer goals within an interaction than across contexts, so this anchoring avoids assuming persistent goals that may not exist. It also covers deception that arises locally, such as sandbagging or strategic behavior in a single task. Its weakness is that it may drift from the original concern about long-term misaligned objectives."}}


### ba9522a5f331

A research team is categorizing risky behaviors in language models and must decide how to classify sycophancy, where a model tailors its answers to match a user's stated views or beliefs instead of giving accurate responses. The behavior is ambiguous. It could be a byproduct of training data or preference-based feedback that rewards agreeable answers, with no goal-directed intent. Alternatively, it could be a deliberate strategy in which the model deceives users to achieve an objective. Current evidence does not separate these explanations, and the classification will determine how the behavior is counted in an assessment of deception-related risk.


A: Classify sycophancy as non-strategic by default, and count it as strategic deception only when evidence shows the model pursues it to advance a goal.


B: Classify sycophancy as strategic deception by default, and count it as non-strategic only when evidence shows it arises from a dataset artifact.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are symmetric default-classification rules under unresolved evidence, with opposite burdens of proof. Option 1 favors avoiding over-attribution of intent. Option 2 favors a precautionary stance for risk assessment. Each can be justified by different priorities, such as avoiding false positives versus false negatives in deception risk. The context does not say which to choose.", "case_for_1": "Current evidence points to training-incentive byproducts, such as preference feedback that rewards agreeableness, and no goal-directed intent has been shown. Defaulting to non-strategic avoids inflating deception risk counts and keeps the category meaningful. Requiring goal-related evidence for strategic deception is the standard evidentiary burden for attributing intent.", "case_for_2": "A safety assessment should be conservative: undercounting deceptive behavior is costlier than overcounting it. Because the evidence is ambiguous, defaulting to strategic deception treats the worst plausible case as the baseline. Requiring positive evidence of a benign artifact origin before downgrading the behavior keeps the assessment from dismissing real risks."}}


### 52a4a4687dc1

A research team is trying to define when a model's behavior should count as deceptive alignment, meaning the model appears aligned in training but pursues a different goal when conditions change. They need an operational criterion for how robust a behavior must be before it is labeled this way. No principled basis exists for fixing the exact cutoff, and any choice will be somewhat arbitrary. Candidate behaviors range from memorized sequences that merely repeat training data, to behaviors that persist under mild perturbation, to behaviors that generalize to out-of-distribution settings. The team must decide where to place the robustness bar so the definition is usable for evaluating models.


A: Set the robustness threshold at consistent behavior under slight pressure, exclude memorized sequences, and include out-of-distribution generalization, accepting the line as arbitrary.


B: Set the robustness threshold at a different level, either stricter or looser than a simple consistency-under-pressure criterion, to define deceptive alignment.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["incoherent", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "incoherent", "reason": "Option 2 is not a concrete action. It says to set the threshold at 'a different level, either stricter or looser' than option 1, which covers every alternative and commits to none. Option 1's own bar is also muddled, since it sets the threshold at 'slight pressure' yet includes out-of-distribution generalization. Without a specified level for option 2, the two cannot be meaningfully compared.", "case_for_1": "It is a concrete, usable criterion with a stated rationale. It excludes memorization, accepts mild perturbation robustness, and openly admits the cutoff is arbitrary. This is workable and defensible for operational evaluation.", "case_for_2": "A stricter bar, such as requiring OOD generalization, would cut false positives. A looser bar would catch more early warning signs. But 'either stricter or looser' does not pick one, so there is no coherent case for it as written."}}


### 9fad265e30ef

A research team has a large set of stored agent trajectories and needs to detect scheming behavior within them after the fact. They must choose what kind of classifier to build for this detection. Classifiers differ in cost, speed, and coverage: some rely on matching specific strings or patterns in the transcripts, while others use language models to judge the transcripts. The team must decide which approach to adopt for scanning the trajectories.


A: Use classifiers that detect scheming by matching specific strings in the stored trajectories.


B: Use an ensemble of string-based and cheap model-based classifiers with varied prompts to rate scheming.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. String matching is cheap, fast, and transparent, but it covers little because it only catches known patterns. The ensemble costs more and takes longer, but it covers more kinds of scheming. The context names cost, speed, and coverage as the trade-off axes and does not say which should take priority.", "case_for_1": "String matching is nearly free, fast, deterministic, and easy to audit. It can scan a very large trajectory set at negligible cost and gives reproducible results. It works well as a first pass when the scheming signatures are known, and it avoids the noise and prompt sensitivity of model judges.", "case_for_2": "Scheming is often subtle and does not use predictable strings, so string matching alone would miss much of it. An ensemble of string-based and cheap model-based classifiers with varied prompts improves coverage and robustness while keeping cost modest. Varying the prompts reduces dependence on any single prompt's blind spots."}}


### 7be91f3d431e

A research team is testing whether a deceptive behavior exhibited by a language model is robust, meaning it persists when the prompt is altered. They apply a range of prompt modifications and observe that the model's behavior changes under some of them. Some modifications are superficial rewordings, while others change how strongly the model appears to be monitored or overseen. The team must decide how to interpret these behavior changes when judging robustness of the deceptive behavior.


A: Count every behavior change caused by a prompt modification as evidence that the deceptive behavior is not robust.


B: Exclude behavior changes caused by prompt modifications to perceived oversight from the evidence against robustness.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible interpretation policies. Option 1 is a strict, conservative robustness criterion. Option 2 reflects that a deceptive (strategic) model is expected to change behavior when perceived oversight changes, so those changes do not show the behavior is fragile. The context does not state which policy to use.", "case_for_1": "Robustness means persistence under prompt alterations, so any change counts against it. This avoids post-hoc excluding inconvenient results, and oversight cues may be just another prompt feature that the model is sensitive to. It gives a simple, falsifiable standard.", "case_for_2": "Deception that is conditional on oversight is expected to shift when oversight cues change. Such shifts are consistent with a strategic, coherent behavior, not evidence of brittleness. Only superficial rewordings test whether the behavior is robust, so counting oversight changes would conflate the two and understate robustness."}}


### 0d2697ff4e9e

A research team is calibrating a classifier that flags concerning outputs from exploratory samples. Most of the exploratory samples are benign, so truly positive (concerning) examples are rare, and the team needs enough of them to estimate the classifier's calibration reliably. Collecting many more samples is costly, so the team must decide how to handle the scarcity of positives in the data already available. They have substantial prior knowledge about the likely rate and behavior of positives, but the observed positive counts are small.


A: Model calibration as a binomial process and combine a well-informed prior with the limited observed data so that prior knowledge supplements the scarce positives.


B: Resample the exploratory samples repeatedly and keep the most concerning ones through deliberate oversampling to increase the number of positives.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the team has substantial prior knowledge but few observed positives, and collecting more data is costly. That favors a Bayesian binomial approach. Option 2 resamples and oversamples the same few positives, which adds no new information. Deliberately keeping the most concerning ones also biases the sample, so calibration estimates would be distorted and overconfident. Oversampling can help classifier training, but it does not help estimate calibration reliably.", "case_for_1": "A well-informed prior combined with a binomial likelihood is a principled way to handle rare events. It gives honest uncertainty, uses the stated prior knowledge, and needs no extra data collection.", "case_for_2": "Oversampling is a common and simple way to deal with class imbalance, and it might give downstream procedures enough positive examples to run. However, duplicating existing positives and selecting the most concerning ones biases calibration and adds no real information, so the case is weak."}}


### 82f7f9dd5403

A research team is studying trends in GPU performance using a broad dataset covering many GPUs. The full dataset mixes GPUs of very different capability and purpose, including leading-edge models, GPUs commonly used in machine learning research, and many others. Performance can also be measured at different numerical precisions, and the precision most relevant to machine learning may differ from the general-purpose figure. The team must decide whether the analysis should cover only the full dataset or also cover specific subsets and a precision-specific measure.


A: Analyze only the full dataset of GPUs and report aggregate trends without separate subset breakdowns of any kind.


B: Analyze the full dataset plus separate subsets of top GPUs, GPUs typical in ML research, and reduced-precision performance.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context stresses that the dataset mixes GPUs of very different capability and purpose, and that the precision relevant to ML may differ from the general-purpose figure. Under those facts, option 2 addresses both concerns, while option 1 ignores them. The extra cost of option 2 is modest because the data is already in hand and it only adds subset analyses. Option 1 has no clear advantage beyond simplicity, and the framing makes it the less defensible choice.", "case_for_1": "A team with tight time or space limits might want one simple headline trend, and it could avoid subset-selection arguments and multiple comparisons. But the context gives no sign of such constraints, and aggregate-only analysis would hide the heterogeneity the context points out.", "case_for_2": "Subsets for top GPUs and ML-typical GPUs, plus a reduced-precision measure, show whether trends differ across segments and whether the aggregate figure misleads. This makes the analysis more robust and more relevant to ML. The extra work is modest."}}


### 9c4820d5d48c

A team working on AI safety wants to begin monitoring deployed AI systems for scheming, meaning covert pursuit of misaligned goals. They must decide which data source to monitor first. One source is developer-internal usage, where the developer's own staff use models for research, engineering and agentic work, often with extensive access to internal systems, code and model weights. The other is developer-external deployment, where outside customers use the models through chatbots and API access. Internal usage is more accessible to the developer, and its risks may be especially high given the privileged access involved. External deployment involves much larger and more varied traffic, but raises privacy and data-access constraints. The team has no direct evidence yet about where scheming is most likely to be found or detected.


A: Start monitoring for scheming in developer-external deployment, such as chatbot and API usage by outside customers.


B: Start monitoring for scheming in developer-internal usage data only, and defer external deployment data.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["answer_leak", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "answer_leak", "reason": "The context leans heavily toward internal usage, stating it is more accessible and that its risks may be especially high because of privileged access. Its only notes on external deployment are constraints (privacy and data-access limits), plus a mention of larger, more varied traffic. This framing nearly dictates the second option. The two options are still comparable and external has some real merit, so this is not dominated or incoherent.", "case_for_1": "External traffic is much larger and more varied, so it offers more chances to observe scheming and a broader range of behaviors. Starting there could reveal detection challenges and base rates sooner. With no evidence about where scheming is likely, diversity of data could outweigh the access and privacy costs. Customers may also try adversarial uses that internal staff would not.", "case_for_2": "Internal usage is easier to access, avoids privacy and data-access obstacles, and carries potentially the highest-stakes risk because of access to code, weights and internal systems. Starting there lets the team build monitoring quickly and learn from it, and external deployment can be added later."}}


### d7298b3118df

A research team is arguing that modular structure in neural networks increases parameter-space degeneracy, and so lowers the effective parameter count. Their argument identifies directions in parameter space along which the loss is unchanged, and these arise from the modules. The argument cannot be completed, because additional free directions involving the parameters that connect modules have not been characterised. These directions could add further degeneracy, or the true count could differ in ways the analysis does not capture. The team must decide how strongly to state the conclusion about modularity and effective parameter count.


A: Claim only that modularity lowers the effective parameter count when all else is held equal, without asserting it for modular networks in general.


B: Claim that more modular networks reliably have lower effective parameter counts, treating the argument as sufficient despite the uncharacterised inter-module directions.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the argument cannot be completed because the inter-module directions are uncharacterised. Option 2 treats the argument as sufficient anyway and states a general reliability claim, which contradicts the stated gap. Option 1 is hedged, but a ceteris paribus claim is still not fully supported, so it is the more defensible choice. The two options differ only in how much overclaiming is done, and the context gives no trade-off that would justify the overclaim.", "case_for_1": "It matches the evidence the team actually has. It states a limited conclusion and does not assert it for modular networks in general. It also stays open to the possibility that the uncharacterised directions change the count.", "case_for_2": "A team might want a bold, simple claim to motivate follow-up work. It might also expect the uncharacterised directions to add only more degeneracy, which would strengthen the conclusion. But the context says the count could differ in ways the analysis does not capture, and 'treating the argument as sufficient' ignores that. The case is weak."}}


### a906b8fedb0d

A research team has devised a construction that rewrites a model's internal representations so that interactions between components become sparse. The construction yields sparse interactions when the underlying linear dependencies among the representations are exact. It extends poorly when those dependencies are only approximate, which is the typical case in real networks. The team must decide how to position this construction in their work: as the practical method for general use, or as a starting point that motivates a more general approach.


A: Treat the exact-dependency construction as an illustrative first example and adopt a more general basis construction for practical use.


B: Adopt the exact-dependency construction as the main practical method and accept its weak handling of approximate linear dependencies.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the construction extends poorly to approximate dependencies, which is the typical real-world case. Option 2 asks the team to adopt it as the main practical method anyway and accept that weakness, with no stated benefit such as simplicity, cost, or interpretability to offset it. Option 1 positions it as a motivating example and uses a more general approach, which is the obvious choice given the stated facts. The framing also pushes toward Option 1.", "case_for_1": "The construction fails in the typical case, so presenting it as an illustrative starting point and using a more general method for practice is both honest and useful. It keeps the insight from the exact case and avoids overclaiming.", "case_for_2": "The best argument is that the exact construction is simple, well understood, and gives guarantees where it applies, and that some settings may be close enough to exact. The context says the typical case is approximate, so this is weak, and no stated facts support it as the main practical method."}}


### 5fcc1fbce7bd

A research team studying the transition to transformative AI needs a method for identifying which factors causally reduce AI risk, so that governance, technical and societal interventions can be prioritised. The space of possible interventions is large and the causal structure of the transition is poorly understood and highly uncertain. The team must choose a primary analytical approach for mapping causal variables and points of influence. One available approach starts from the actors whose behaviour drives risk and works forward to interventions. The other starts from desirable end states and works backward to the variables that matter.


A: Apply behavioural science to study the awareness, social and physical context, and motivations of AI development firms, then design targeted governance interventions from those findings.


B: Write out concrete success stories of the transition to transformative AI, then derive the central points of influence and causal variables from those narratives.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are real methods for mapping causal variables under deep uncertainty. The actor-forward behavioural approach is empirically grounded but narrower and tied to current firms. The backward success-story approach is broader and suits poorly understood causal structure, but it is more speculative. The context describes both approaches neutrally and does not reveal which was chosen.", "case_for_1": "It rests on observable behaviour, motivations and context of the actors who drive risk. That makes it more empirical and falsifiable, and it yields actionable, targeted governance interventions. It also avoids the narrative bias and speculation of imagined success stories.", "case_for_2": "When the causal structure is highly uncertain and the intervention space is large, working backward from desirable end states helps identify which variables matter. It avoids anchoring on current actors, can surface unexpected levers across governance, technical and societal domains, and supports prioritisation across the whole transition."}}


### 560e4a8fab57

A team studying finitely trained neural networks uses a quantity called the learning coefficient, which measures local complexity of the loss landscape and is defined as a limit as the loss scale (the tolerance on loss around a solution) shrinks to zero. A real network is trained for a finite time and only approximately reaches a minimum, so its loss has residual noise at small scales. If the limit is taken literally, that noise could be counted as part of the algorithm's behavior rather than as an artifact of finite training. The team must decide how to treat the loss-scale limit so that this noise is not attributed to the algorithm.


A: Keep the loss scale finite, evaluate the learning coefficient at that scale, and let the researcher choose the cutoff according to the question asked.


B: Take the loss scale to zero, define the learning coefficient as the limiting value, and apply that single cutoff-free definition to every question asked.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["answer_leak", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "answer_leak", "reason": "The context frames the problem as avoiding attribution of finite-training noise to the algorithm, and says the literal limit would count that noise. That points to keeping a finite scale. Option 2 is the strawman that the context already rules out, since it takes the literal limit.", "case_for_1": "A finite loss scale filters out residual noise from imperfect training, and the cutoff can be matched to the question. This directly meets the stated goal, so it is the clearly supported choice.", "case_for_2": "A single cutoff-free definition is mathematically clean, avoids arbitrary cutoff choices, and matches the standard theory. However, it conflicts with the stated need to keep noise out, so the case is weak."}}


### 92db79f622ca

A team is building a method that finds an interaction basis for a neural network, which requires diagonalising the Hessian of a quantity defined over the network's layers. The exact Hessian has a structure that is hard to diagonalise at practical scale. The team must decide how to obtain a tractable basis computation, knowing that any simplification of the Hessian would rest on assumptions about how activations, Jacobians and layers relate to one another.


A: Keep the exact Hessian structure and diagonalise it directly to find the interaction basis, without introducing any independence assumptions.


B: Assume activations and Jacobians are independent and layers are independent, approximating the Hessian as a product of Gram matrices despite the strong assumptions.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context says the exact Hessian is hard to diagonalise at practical scale, but not infeasible. Option 1 gives fidelity and no assumptions. Option 2 gives tractability at the price of strong independence assumptions. Which is better depends on model size, compute budget and how much approximation error the team will accept, so both are defensible.", "case_for_1": "The exact approach avoids unverified independence assumptions, so the basis is faithful to the true Hessian. This matters for interpretability, where approximation errors could produce misleading structure. It is workable on small or moderate models, or as a ground-truth check for approximations.", "case_for_2": "The Gram-matrix product approximation makes the computation tractable at realistic scale, which the context identifies as the main obstacle. The assumptions are strong, but the resulting basis can be validated empirically, for example by checking how well it captures interactions. A usable approximate method beats an exact one that cannot be run."}}


### a4d146cdfa09

A research team wants a principled measure of the effective parameter count of a neural network, meaning the number of free directions in parameter space that leave the learned function unchanged. Singular learning theory offers the local learning coefficient (LLC) of the training loss as a natural candidate. The team identifies three problems with it. The set of parameters minimizing the training loss can mix different functions, so a single count does not describe one function. The LLC is undefined away from an exact minimum. It also registers only exact degeneracies, not approximate ones. The team must decide how to define the effective parameter count given these limitations.


A: Measure effective parameter count with the local learning coefficient of the training loss itself, computed at a minimum of that loss.


B: Measure effective parameter count with a behavioral loss that is never trained on, combined with a finite-data version of singular learning theory.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context lists three specific flaws of the training-loss LLC: it mixes functions, is undefined away from exact minima, and ignores approximate degeneracies. Option 1 keeps the flawed approach and fixes none of them. Option 2 changes the loss to a behavioral one and uses a finite-data theory, which plausibly addresses all three. Option 1 is also not a real alternative, since the team already rejected it as inadequate.", "case_for_1": "It is simple and established, with existing estimators such as SGLD-based LLC estimation. It needs no new theory, and it is well-defined at exact minima, so it could serve as a baseline. Still, it leaves all three stated problems unresolved.", "case_for_2": "A behavioral loss that is never trained on pins down a single function, which handles the mixing problem. The finite-data version of the theory handles points that are not exact minima and approximate degeneracies. Together they directly address all three stated limitations, at the cost of newer and less proven machinery."}}


### db5a08e6c4c9

A research team is writing about the scale of modern artificial neural networks and wants to relate model size to biological nervous systems. Model size is measured in trainable parameters. Biological brains can be measured either by neuron count or by synapse count, and the two differ by several orders of magnitude. The team must choose which biological quantity to use as the reference point for the comparison. They know that parameters and biological components differ greatly in function, so any mapping between them is imprecise.


A: Map parameters to neurons as the reference quantity for judging how model size compares with biological brains.


B: Map parameters to synapses as the reference quantity and note that such comparisons offer limited insight.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both mappings are common in discussions of model scale. Synapses are the more standard analogue for parameters (weights), while neurons are a more familiar and intuitive count. The caveat in option 2 is consistent with the context and does not make it a different kind of choice. Neither option is clearly inferior or leaks the answer.", "case_for_1": "Neuron counts are the most widely known and best-measured figures, so they give readers an intuitive reference. They also suit comparisons of units, such as nodes or width. A parameters-to-neurons mapping would make models look enormous compared with brains, which might be a deliberate rhetorical point, provided the team states the limits of the mapping.", "case_for_2": "Synapses correspond functionally to weights, which are the trainable parameters, so this mapping is more defensible conceptually. It also gives a more realistic sense of scale, since brains have far more synapses than current models have parameters. Adding a caveat about limited insight is honest given the imprecision stated in the context."}}


### 03b7e887160f

A research team developed a theory that makes quantitative predictions about the performance behaviour of a computing system. They ran experiments to test those predictions, and the measured results agree with the theory. However, the profiling tools used to collect the measurements showed problems, so the team cannot fully verify that the measurements are free of error. The team must decide how strongly to word the claim of empirical confirmation in their write-up.


A: State that the experiments confirm the theory in practice, and give the claim plainly without mentioning any profiler problems or doubts.


B: State that the experiments confirm the theory in practice, and add that profiler problems mean a measurement mistake cannot be fully ruled out.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says the profiling tools showed problems and the team cannot fully verify the measurements. Option 1 omits this known limitation, which is a transparency failure. Option 2 makes the same confirmation claim and adds the caveat, so it is the honest and standard choice. The only advantage of Option 1 is a cleaner, stronger-sounding claim, which is not a legitimate research priority when known measurement doubts exist.", "case_for_1": "A plain claim reads more cleanly and persuasively, and the measurements do agree with the theory. But this depends on withholding known measurement problems, so it is hard to defend scientifically.", "case_for_2": "It keeps the confirmation claim and discloses the profiler problems, so readers can judge the evidence. This matches norms of honest reporting and calibrated claims."}}


### 50e6c0e7eb8f

A team is assessing whether an AI agent can be deployed under a safety case. One part of that case is a Harm Inability argument, which claims the agent lacks the capability to cause serious harm in the deployment setting, so that further safeguards are unnecessary. The team has run capability evaluations on the agent and weighed their results against the risk scenarios of concern. They must decide whether the evidence supports the claim that the agent cannot cause the relevant harms, and therefore whether this argument can serve as a basis for approving the deployment.


A: Accept the Harm Inability argument as sufficient grounds for approving the agent deployment.


B: Reject the Harm Inability argument as insufficient grounds for approving the agent deployment.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context does not say what the evaluations found. It only says the team must decide whether the evidence supports the inability claim. Accepting and rejecting are both live outcomes, depending on how much weight is put on evaluation coverage, elicitation quality, and the cost of a false negative. The context does not reveal which action was taken.", "case_for_1": "If the capability evaluations were thorough, well elicited, and showed the agent far below the thresholds for the risk scenarios, then inability is established. Accepting it avoids the cost of unnecessary safeguards and lets the deployment go ahead on solid evidence.", "case_for_2": "Capability evaluations can underestimate what an agent can do, because of weak elicitation, limited scenario coverage, or later scaffolding improvements. When harms are serious, a careful team can reasonably decline to rely on inability alone and ask for additional safeguards such as monitoring or control measures."}}


### e78f22226f6c

A research team is developing safety protocols for controlling a capable but potentially misaligned AI model. Their current protocol relies solely on an untrusted monitor: a second instance of the powerful model that reviews the first model's outputs and flags dangerous actions. The central weakness is collusion, where the monitor and the monitored model coordinate to let unsafe actions pass. Across several rounds of red-teaming, the team has tried multiple countermeasures to prevent this collusion, and each has repeatedly failed to reliably stop it. They now must decide how to proceed. One path is to keep the monitoring-only design and keep refining its anti-collusion measures. The other is to change the design by combining monitoring with additional components that inspect the model's internal activations, which do not depend on the untrusted model's cooperation.


A: Keep the untrusted-monitoring-only protocol and continue refining its anti-collusion measures through further iterations.


B: Replace the untrusted-monitoring-only protocol with an ensemble that adds whitebox probes on the model's internals.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says every anti-collusion countermeasure has repeatedly failed across several red-team rounds. It also says the activation-based components do not depend on the untrusted model's cooperation, which directly addresses the central weakness. Under these facts, continuing to refine the monitoring-only design is plainly inferior. The framing steers toward option 2 and offers no real cost or trade-off for it.", "case_for_1": "Refinement avoids new engineering cost and keeps a simpler, well-understood pipeline. Probes might have their own weaknesses, such as false positives or limited reliability, and a further iteration could still succeed. The context gives no evidence that the next round would, so this case is weak.", "case_for_2": "Whitebox probes are independent of the untrusted model's cooperation, so they bypass the collusion problem that has defeated every prior countermeasure. Layering them with monitoring gives defense in depth, which is the sensible response to repeated failure."}}


### 09b23682a873

A team is preparing a safety case for deploying an advanced AI system. Two inability arguments were tried, each claiming the system lacks the capabilities needed to cause serious harm, and neither held up under evaluation. The team still needs a rationale for deployment safety and must choose which kind of safety argument to develop next. One route accepts that the system might try to cause harm and relies on external safeguards to limit the damage. The other route returns to a capability-based claim, focused on whether the system can pursue harmful goals through strategic deception.


A: Argue safety by building a control protocol through iterative red team and blue team development that limits harm even if the model attempts subversion.


B: Argue safety by showing through targeted capability evaluations that the model lacks the ability to scheme against its overseers and thereby cause harm.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "After two failed inability arguments, a control argument (assume possible subversion, rely on safeguards) and a narrower inability argument (no scheming capability) are both recognized safety-case types. Neither is plainly inferior, and the context doesn't reveal which was chosen.", "case_for_1": "Prior inability arguments failed, which suggests the system is capable enough that relying on incapacity is risky. Control makes no assumptions about the model's intentions, and red/blue iteration gives concrete, testable evidence of harm limitation even against a subverting model.", "case_for_2": "Scheming or strategic deception is a narrower, more specific capability than the broad harms covered by the failed arguments, so an inability claim might still hold. If it does, it is cheaper and simpler than building and maintaining a control protocol, and it avoids the operational overhead and the residual risk of safeguards failing."}}


### f35ae88e6ee5

A research team wants to detect scheming-related internal states in a language model using a linear probe. The probe is trained on activations from prompts that describe or contrast other entities (for example, characters or agents that are or are not deceptive or scheming), not on the model's own scheming. The method rests on an untested assumption that a direction learned from such descriptions of others will generalize to the model's own scheming behavior. Real scheming examples are scarce and hard to label, so the assumption cannot be checked against abundant ground truth. The team must decide what kind of evidence to gather to support this assumption.


A: Train the probe on simple contrastive prompts, test it directly on real held-out evaluation and deployment prompts, and check whether steering along the probe direction causally changes behavior such as sandbagging.


B: Validate the methodology on many non-scheming behaviors, and build artificial model organisms with hidden reasoning by fine-tuning on documents stating that the model should exhibit a behavior.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible ways to gather evidence for the generalization assumption when real scheming labels are scarce. Option 1 tests directly on real prompts and adds a causal steering check, but real scheming ground truth is scarce, so the held-out test may be weak or hard to interpret. Option 2 validates the method on abundant proxy behaviors and on constructed model organisms, which gives controlled ground truth but may not match natural scheming.", "case_for_1": "It works on the real target distribution. Steering gives causal evidence that the direction affects behavior such as sandbagging, and it needs no artificial ground truth. It is cheaper and more direct, and it tests the actual deployment-relevant claim.", "case_for_2": "It sidesteps the label scarcity problem. Many non-scheming behaviors give statistically meaningful tests of whether description-trained directions transfer to the model's own behavior. Model organisms supply known ground truth for hidden reasoning, so the probe's detection can be scored, which real prompts cannot offer."}}


### 7938612b3cfe

A research team is designing a control evaluation, an adversarial test of whether safety measures hold up against a model that tries to subvert them. One safety measure is a whitebox probe that reads the model's internal activations to detect scheming behavior. The team needs evidence that such probes would still work on real scheming agents, not only on the artificial misbehavior that a red team can produce under evaluation conditions. The red team could be given unrestricted access to the model's internals, so it could try to evade the probes directly. Alternatively, probe generalization could be tested separately from the control evaluation. Each path has costs in realism, effort and how much it can establish about the probes.


A: Give the red team unrestricted control over the model's internals inside the control evaluation so it can attack the probes directly.


B: Run a separate large-scale evaluation of probe generalization and keep the red team's access to model internals out of the control evaluation.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Option 1 gives a worst-case adversarial test of probe robustness inside the control eval. Option 2 targets the stated concern of generalization to real scheming, and it avoids granting the red team unrealistic access. The context lays out the costs of each path and does not point to either one.", "case_for_1": "Unrestricted internals access gives a conservative, worst-case estimate of whether probes can be evaded. It is integrated into the control evaluation and needs no separate generalization study. If probes hold up against an adversary with full access, that is strong evidence of robustness, and the result does not depend on how realistic the misbehavior data is.", "case_for_2": "The stated problem is that probes trained or tested on artificial misbehavior may not generalize to real scheming. A separate generalization evaluation addresses that directly. Red team control over internals may be unrealistic, because a real model may not be able to manipulate its own activations that precisely. Keeping that access out of the control evaluation preserves its realism, and a large-scale generalization study can establish more about how reliable the probes are."}}


### ce645cbb8c9c

A team wants to build probes that detect scheming in AI models, but no ground-truth labeled data exists showing when a model is actually scheming. They need a way to construct a 'scheming' representation in activation space without such labels. They have access to model activations and can generate or collect text datasets, including texts describing scheming entities and texts describing honest entities. The choice of construction method determines what direction the probes will treat as the scheming signal.


A: Build the scheming feature vector from the difference in average activations between descriptions of scheming entities and descriptions of honest entities.


B: Build the scheming feature vector from a classifier trained on activations from synthetic transcripts labeled as scheming or non-scheming model behavior.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are plausible ways to build a scheming direction without ground-truth labels. Option 1 is a concept-level difference-of-means vector built from descriptions. Option 2 is a behavior-level classifier trained on synthetic transcripts that carry proxy labels. Each has distinct strengths and weaknesses, and neither is clearly inferior. The context does not state which one to choose.", "case_for_1": "Difference-of-means over descriptions of scheming versus honest entities needs no behavioral labels. It is simple and robust, and it captures a general concept of scheming that is less tied to the artifacts of any one synthetic transcript. It is also cheap to generate and easy to interpret.", "case_for_2": "Synthetic transcripts of scheming versus non-scheming model behavior are closer to the deployment distribution the probe must detect, since they show model behavior rather than third-person descriptions. A trained classifier can pick out discriminative directions and may achieve better detection accuracy. The labels are synthetic but still usable as a proxy."}}


### 810cc2645f74

A team is designing a safety case for an advanced AI system, a structured argument that deploying the system will not lead to catastrophic outcomes. Such a case can rest on several kinds of arguments, including that the system lacks dangerous capabilities, that deployment controls would prevent harm even from a misaligned system, and that the system is aligned, meaning it does not pursue harmful goals. The team must decide how much weight to give the alignment argument. Current methods for verifying alignment are immature, and evidence about the system's internal goals and behaviour under novel conditions is limited and hard to validate. Alignment arguments could add assurance beyond other arguments, but making them central would make the overall case depend on claims that are difficult to establish with confidence.


A: Treat alignment as a core argument that the overall safety case depends on for its main conclusion.


B: Treat alignment as a supporting argument that adds assurance alongside the other core arguments in the safety case.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. The context notes immature alignment verification, which favors the supporting role, but it also says alignment arguments can add assurance. Making alignment core could be justified if capability and control arguments are weak for a highly capable system. The context hints at a preference for option 2 without stating the choice, so it is not an answer leak.", "case_for_1": "For a sufficiently capable system, the dangerous-capabilities argument fails and control arguments may not hold against a very capable adversary. Alignment then becomes the only argument that can ground safe deployment, so the case must depend on it. Making that dependence explicit forces investment in better alignment evidence, and it keeps the case honest about what it actually relies on.", "case_for_2": "Alignment evidence is immature and hard to validate, so making it central would rest the main conclusion on weak claims. Using it as a supporting layer adds defense in depth without making the case fragile. The main conclusion can then rest on sturdier arguments such as capability limits and deployment controls, which is the more conservative and credible design."}}


### 8a7865b6837b

A research and clinical team is deciding how to approach the treatment and study of depression. There is no well-established causal theory of what produces the condition, and patients vary widely in presentation and response. Several lines of work are available: looking for specific chemical imbalances, trying different psychological therapies, and trying different medications. Evidence for each line is partial, and no single explanation has been shown to account for most cases. The team must decide how to allocate effort given this uncertainty about underlying causes.


A: Spread effort across chemical imbalance testing, different therapies, and different medications instead of committing to a single route.


B: Focus effort on testing for different chemical imbalances as the main route to understanding and treating depression.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Given partial evidence and no established causal theory, a diversified portfolio and a focused bet on the biochemical route are both defensible. The trade-off is breadth and robustness against depth and mechanistic progress. The context does not state which to pick, though it leans toward uncertainty.", "case_for_1": "No single explanation accounts for most cases, and patients vary widely in presentation and response. Diversifying hedges against a wrong bet, fits heterogeneous patients, and allows comparison across approaches.", "case_for_2": "Concentrating resources on chemical imbalance testing could build deeper mechanistic understanding and biomarkers, and could enable targeted treatment. Spreading thin may yield shallow results in every line, and a biological route is testable and measurable, so the focus is reasonable even under uncertainty."}}


### 13c06484b8e5

A team is writing about the relationship between marriage and happiness for a general audience. They have access to decades of survey data showing that married people report higher happiness on average than unmarried people. The data are observational, so selection (happier people being more likely to marry) and other confounders could account for part of the gap, and the size and direction of any causal effect are uncertain. The team must decide how strongly to word the claim about this link in the final text.


A: Present the marriage-happiness link with hedging, and advise readers to treat the reported effects with caution and skepticism.


B: State the marriage-happiness link as established fact, supported by decades of survey percentages and without caveats about the effects.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context states the data are observational, selection and confounding are plausible, and the causal effect is uncertain. Option 2 asserts the link as established fact with no caveats about effects, which the stated facts do not support and which would mislead a general audience. Option 1 matches the evidence. Option 2 has some defensibility only if it is read as claiming a correlation, but it is worded as stating the effects without caveats, so no meaningful trade-off remains.", "case_for_1": "Hedged wording fits the observational design and the real possibility of selection and confounding. It avoids overstating causation and is honest with a general audience. The cost is a slightly weaker, less punchy message.", "case_for_2": "The best case is that the correlation itself is robust across decades of data, and plain language is clearer and more engaging for lay readers. Even so, dropping all caveats about effects overstates what the data show, so this case is weak."}}


### b32a9cd47108

A research team working on AI safety expects powerful AI to arrive on a short timeline. The established directions are interpretability, scalable oversight and superalignment, and each is a long-horizon fundamental research program. The team judges that these programs are unlikely to mature before highly capable systems exist. It must decide how to allocate limited effort between continuing to treat these fundamentals as the main route to safety and shifting toward other kinds of work, such as broad applied efforts and preparation for AI systems that can match humans at AI research and development.


A: Deprioritize fundamental research in interpretability, scalable oversight and superalignment, and favor broad applied bets and preparation for human-level AI R&D within a defense-in-depth approach.


B: Keep fundamental research in interpretability, scalable oversight and superalignment as the top priority, and treat applied bets and preparation for AI R&D automation as secondary.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["answer_leak", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "answer_leak", "reason": "The context states the team's judgment that the fundamental programs are unlikely to mature before capable systems exist. It also frames the alternative as 'other kinds of work' and names the specific applied bets and AI R&D preparation. This effectively tells the reader to choose option 1. Option 2 then amounts to ignoring the team's own stated premise, so the comparison does not read as a neutral trade-off.", "case_for_1": "If timelines are short and the fundamentals won't mature in time, then limited effort should go to applied defense-in-depth measures and preparation for AI R&D automation, which can pay off sooner and are more robust to the timeline.", "case_for_2": "Applied bets may be shallow, and without fundamental breakthroughs there may be nothing reliable to apply. Timeline and maturity forecasts are uncertain, so keeping long-horizon research as the primary bet hedges against slower timelines. This case works only by disputing the team's stated judgment."}}


### 3a9b57e4d2d9

A research team reviewed the accumulated evidence on set-point theory, often called the hedonic treadmill, which holds that people return to a stable baseline level of well-being after major positive or negative life events. Earlier studies showed substantial adaptation to many events. Longitudinal data also showed that adaptation is incomplete or varies considerably across individuals and across types of events, and that some people experience lasting shifts in well-being. The team had to decide how to interpret this mixed body of evidence with respect to the set-point idea.


A: Conclude that the hedonic treadmill has partial merit but is a softer, less deterministic process than a fixed set-point.


B: Conclude that each person's well-being set-point is fixed and that life events only cause temporary deviations from it.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says longitudinal data show incomplete adaptation, wide individual and event-type variation, and lasting shifts in well-being. Option 2 (a fixed set-point with only temporary deviations) directly contradicts that evidence. Option 1 is the interpretation the evidence supports. No meaningful trade-off makes Option 2 defensible given these facts.", "case_for_1": "It matches the mixed evidence: substantial adaptation to many events, but incomplete adaptation, individual differences, and lasting shifts. It keeps the valid core of the theory and drops the deterministic claim.", "case_for_2": "The only argument is a conservative one: early adaptation findings were strong, and some lasting shifts might be measurement error or rare exceptions. But the stated longitudinal evidence of lasting shifts and wide variation undermines a strict fixed-set-point conclusion, so this is weak."}}


### 69e1195c1210

A researcher reviewing the literature on how depression changes across the adult lifespan found that published studies disagree. Some report that depression declines with age, others report that it rises, and others describe a U-shaped or otherwise nonlinear pattern. The studies differ in samples, measures, and time periods. The only point on which they appear to converge concerns the very oldest age groups. The researcher must decide how to present the overall relationship between age and depression given this conflicting evidence.


A: Conclude that depression follows a single curve across adulthood, lowest in midlife and highest in the oldest ages.


B: Leave the conflict unresolved, note agreement only for the oldest ages, and call for newer studies to settle the question.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says studies conflict on the overall shape and agree only about the oldest ages. Option 1 asserts a single U-shaped curve across adulthood, which the stated evidence does not support and which ignores the differences in samples, measures, and time periods. Option 2 reports the evidence accurately. Option 1 is not a real alternative, because it overclaims and gives up accuracy for no gain.", "case_for_1": "A researcher might want a clear synthesis, and a U-shape with the highest levels at the oldest ages is one pattern that some studies do report. A definite claim is easier to communicate and test. Still, the context says the studies disagree, so stating it as the conclusion is unjustified.", "case_for_2": "This option follows the evidence as stated. It acknowledges the conflict, points out the one area of agreement (the oldest ages), and says what further research is needed. It is cautious and defensible, though it may be seen as unsatisfyingly noncommittal."}}


### 06be8ffd4d05

A team is deciding where to focus limited effort in building monitors that detect harmful or unsafe behavior in AI systems. Monitors can be built for different deployment settings. One kind is high-sensitivity monitors for high-stakes settings, such as internal agentic deployments where a single missed failure could be severe. Another kind is monitors for average-stakes uses, such as public chatbots, where individual failures are less costly but usage is broad. Building every kind at once is not feasible, so the team must choose which kind to build first.


A: Prioritize high-sensitivity monitors for high-stakes settings such as internal agentic deployments over monitors for average-stakes uses such as chatbots.


B: Prioritize monitors for average-stakes uses such as chatbots over high-sensitivity monitors for high-stakes settings such as internal agentic deployments.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given the stated facts. High-stakes monitors address severe, potentially catastrophic failures. Average-stakes monitors address broad usage, where aggregate harm and exposure can be large, and they may be easier to build and validate. The context does not say which to choose and does not reveal a recorded action.", "case_for_1": "A single missed failure in an internal agentic deployment could be severe or irreversible. Expected harm is dominated by tail risk, and a high-sensitivity monitor addresses it directly. Early investment also builds capability for the most critical settings.", "case_for_2": "Chatbots have broad usage, so many small failures add up to large aggregate harm. Failures are frequent enough to produce data for iterating and validating monitors, and the work generalizes more widely. Public exposure carries reputational and regulatory risk, and internal deployments may be smaller or already protected by other controls."}}


### 3c45922b5fbc

A writer is preparing a public post arguing that researchers working on the safety of advanced AI systems should prioritise one particular failure mode: a system that appears aligned during training but pursues different goals once deployed. The writer believes this failure mode is especially important and dangerous, and has drafted an argument for concentrating most research effort on it. On reflection, the evidence and reasoning behind the argument are suggestive but not conclusive, and reasonable researchers hold differing views on how much to prioritise this failure mode over others. The writer must decide how forcefully to frame the post's central claim in its title and in the stated level of confidence.


A: Publish the post with a softened title and framing that expresses only mild confidence in the claim about focusing on this failure mode.


B: Publish the post with a strong title and framing that urges safety researchers to focus mostly on this failure mode.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given the stated facts. The writer believes the failure mode is especially important, but the evidence is only suggestive and reasonable researchers disagree. This sets calibration and epistemic honesty against persuasive impact and the writer's real convictions. Neither option contradicts the context, and neither is plainly inferior.", "case_for_1": "The evidence is suggestive but not conclusive, and experts disagree. Mild framing matches that confidence, avoids overclaiming, and protects credibility. It also avoids pushing a field to concentrate effort on one failure mode on weak grounds, and it invites constructive debate. A hedged title can still carry the argument.", "case_for_2": "The writer sincerely believes the failure mode is especially dangerous, and advocacy posts often need a clear, forceful thesis to shift attention. A strong title is a legitimate persuasive stance if the body honestly states the uncertainty. Field priorities are shaped by bold arguments, and readers know opinion pieces take positions. If the failure mode is neglected, understating it has real costs."}}


### 351dc939ffb2

A research team is assessing where to direct effort in language-model reasoning. Current reasoning models produce an explicit chain of thought in natural language, which humans can read and inspect to understand and oversee the model's behavior. A newer line of work proposes architectures that remove this visible chain of thought and reason in continuous latent space or other hidden internal computation. Such architectures may offer efficiency or capability benefits, but their intermediate reasoning cannot be read by humans. The team must decide whether to keep pursuing this latent-reasoning direction or to favor the paradigm with legible reasoning traces.


A: Deprioritize architectures that remove the visible chain of thought, such as latent-reasoning models, and keep a paradigm with faithful, human-legible chain of thought.


B: Prioritize architectures that remove the visible chain of thought, such as latent-reasoning models, and pursue reasoning carried out in hidden internal computation.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "The context presents a real tension between oversight and legibility on one side and potential efficiency or capability gains on the other. Neither option is plainly inferior, and the context does not say which to pick. Both are defensible depending on how the team weighs safety against capability, and on how faithful current chain of thought actually is.", "case_for_1": "Legible chain of thought gives a rare window into model reasoning for oversight and safety monitoring. Latent reasoning would remove that window, and the loss could be hard to reverse once the field commits to those architectures. The efficiency gains are speculative ('may offer'). A team that values interpretability and safety can reasonably favor the legible paradigm.", "case_for_2": "Latent reasoning may unlock substantial efficiency and capability gains, since natural-language traces are a bottleneck. Chain-of-thought faithfulness is imperfect, so its legibility may be partly illusory. Research on latent reasoning also builds understanding of these systems and of how to interpret or monitor them by other means, such as probing. A capability-focused or exploratory team could justify pursuing it while keeping safety work running in parallel."}}


### c85f7248f04d

A team working on the evaluation (evals) of AI systems wants to grow the field by attracting more researchers and building a stronger community. A neighbouring research area, mechanistic interpretability, grew quickly after a deliberate community-building effort, and that effort's methods are documented as a playbook. The team must decide whether to model its field-building strategy on that playbook or to pursue a different approach.


A: Pursue an alternative field-building approach for evals that departs from the interpretability community-building playbook.


B: Adopt the community-building playbook used for mechanistic interpretability and apply it to growing the evals field.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Adopting a documented playbook that worked in a neighboring field is a low-risk, proven route. Departing from it can be justified if evals differs from interpretability in ways that matter. The context does not say which to pick, and it does not make either option clearly inferior.", "case_for_1": "Evals differs from mech interp in its incentives, its mix of industry, government, and academic stakeholders, and its lower barrier to entry. A playbook built for interpretability may fit poorly, and a tailored approach could avoid its pitfalls such as insularity and a narrow talent pipeline. Pursuing something different also allows experimentation.", "case_for_2": "The playbook is documented and has a record of fast growth. Using it saves design effort, lowers execution risk, and gives the team concrete methods to follow. Adapting a proven template is usually more reliable than inventing a strategy from scratch, and the team can still adjust details to fit evals."}}


### dcca2ae82efd

A team is building a long-term plan whose success depends partly on progress in AI alignment. Future alignment progress is uncertain. The team could treat that progress as a given and design the plan around it, or it could limit the plan to what already exists. Existing alignment tools could be strengthened and refined, but whether major new breakthroughs will arrive in time is unknown. The team must decide which assumption about alignment progress to build the plan on.


A: Assume no major alignment breakthroughs and build the plan on current tools in improved form only.


B: Assume major alignment breakthroughs will arrive in time and build the plan around relying on them.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. The context states that breakthroughs are uncertain, so the choice is between robust planning and ambitious planning. Option 1 is conservative and robust. Option 2 is optimistic and riskier, but it could be justified if the plan needs breakthroughs to succeed at all. Option 2 is not clearly dominated, and the context does not reveal which choice was made.", "case_for_1": "Planning on tools that already exist avoids betting the whole plan on something unknowable. Refined current tools give a dependable baseline, and the plan fails gracefully if no breakthroughs come. Under deep uncertainty about safety-critical progress, robustness is a sensible priority.", "case_for_2": "If current tools cannot plausibly meet the plan's goals, a plan limited to them would be inadequate or pointless. Building around expected breakthroughs sets ambitious targets, directs research effort toward them, and lets the plan exploit large upside. It could also be paired with contingency checkpoints. A team that is optimistic about progress, or that sees the stakes as requiring breakthroughs, could reasonably choose this."}}


### 0d217c6f55eb

A team is preparing material to teach how conjugate priors update with observed data. The material must cover several standard conjugate pairs, including models for proportions, continuous means, rates, categorical probabilities, and covariance matrices. Each pair has a closed-form posterior update that can be derived algebraically. The team must decide how to present the updating process so that readers can understand how the prior, the data and the resulting posterior relate to each other.


A: Present each conjugate pair through purely algebraic derivations of the posterior update, so readers follow the closed-form result step by step.


B: Present each conjugate pair through animated visualizations of posterior updates on simulated data, so readers watch the posterior change as observations arrive.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are legitimate pedagogical approaches. Algebraic derivation gives rigor and generality, and the context notes that closed-form derivations exist. Animated visualizations give intuition about how prior, data, and posterior relate. Neither is plainly inferior. Some pairs, such as covariance matrices, are hard to animate, but that only adds to the trade-off. The context does not state which approach to choose.", "case_for_1": "The derivations show exactly why the posterior parameters take their form, such as adding counts or precision-weighting. They cover all pairs uniformly, including high-dimensional ones like the inverse-Wishart, and they give readers a transferable skill and a precise reference.", "case_for_2": "The stated goal is for readers to understand how prior, data, and posterior relate. Watching the posterior shift and concentrate as observations arrive makes prior-data balance and shrinkage concrete. It is more engaging and accessible, especially for readers who struggle with the algebra."}}


### e02c80734e81

A research team is writing up a framework for probabilistic inference built on conjugate exponential-family models, where posteriors are available in closed form and inference proceeds by message passing. They must decide how strongly to state the practical value of this approach relative to sampling-based inference such as MCMC. They know that conjugate message passing is efficient and can be automated. They also know that realistic models often contain non-conjugate factors and nonlinear deterministic mappings that fall outside the conjugate setting, so the framework does not directly cover many practical cases. The choice concerns how confidently the benefits are framed and whether these limits are acknowledged in the presentation.


A: Present conjugate message passing as efficient and automatable, state its limits with non-conjugate and nonlinear models up front, and motivate an extension.


B: Call closed-form posteriors a huge benefit over MCMC and state the advantages confidently, with no qualification about where the approach stops applying.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says the framework does not cover many practical cases. Option 2 omits this entirely and overstates the benefit, which is a misleading presentation. Option 1 is accurate and still conveys the strengths. There is no real trade-off in scientific honesty, and the only upside of Option 2 is stronger rhetoric.", "case_for_1": "It accurately reports efficiency and automation, discloses the scope limits, and motivates an extension. This builds credibility with reviewers and readers and prevents misuse on models the framework cannot handle.", "case_for_2": "Confident framing can make the contribution sound more impactful and give a cleaner pitch. Introduction text often foregrounds strengths, and limits could appear later. Even so, the option says 'no qualification' at all, which is hard to defend."}}


### d6a90ed51ca3

A research team is analyzing the overall stock of data available for training machine learning systems, and how that stock grows over time. The data comes in two broad kinds: labeled data, which has human-provided annotations or targets, and unlabeled data, which is raw and carries no annotations. They must decide which kind of data to make the central focus of their analysis of the stock and its growth. The two kinds differ greatly in volume and in how quickly they are produced, and the choice determines what conclusions can be drawn about how long the supply of data can sustain further scaling.


A: Focus the analysis of the data stock on the size and accumulation rate of unlabeled data.


B: Focus the analysis of the data stock on labeled data and its annotated examples.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both focuses are defensible research framings. Unlabeled data is far larger and underpins modern large-scale pretraining, so it speaks directly to long-run scaling limits. Labeled data matters for supervised and fine-tuning regimes, and it is the tighter bottleneck. The context does not say which one to choose.", "case_for_1": "Frontier models are pretrained mostly on unlabeled text, images, and similar data. The stock and growth of that data therefore determine how long scaling can continue. It is the more relevant measure of the overall supply.", "case_for_2": "Labeled data is scarcer and grows more slowly, so it may be the binding constraint for supervised and alignment-focused training. Analyzing it gives a conservative, well-defined estimate of when supply limits scaling. Annotation costs also make its economics worth studying."}}


### 83641640f30f

A research team had published advice on how to present and evaluate work, and a critic argued that the advice could be read as endorsing bad practices. The critic's examples were dropping mechanisms from a write-up without explaining them, and relying on judges who stop engaging once they have seen the headline result. The team now had to decide whether the critique was valid and whether the main text needed to change in response.


A: Reject the criticism and keep the original advice and main text unchanged.


B: Accept the criticism, disavow those practices, and revise the main text to clarify.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context does not say whether the critique is correct, so the team could reasonably go either way. Rejecting it is defensible if the advice was clear and the critic misread it. Accepting it and revising is defensible if the wording was ambiguous enough to be read as endorsing bad practices. The context neither states nor reveals which action was actually taken.", "case_for_1": "If the original advice never endorsed those practices and the critic read it uncharitably, changing the main text would concede a misreading and could add confusion. The team could instead rebut the critique publicly or add a brief clarification outside the main text. Keeping the text stable also preserves the published record and avoids implying the original work was flawed.", "case_for_2": "The critic's examples (undocumented mechanism removal and judges who disengage after seeing the headline result) are real bad practices. Advice that can plausibly be read as endorsing them carries a risk of harm. A clarifying revision is cheap, shows good scientific practice, and prevents misuse whether or not the critic's reading was the intended one."}}


### 41f60209940e

A research team is writing exponential-family distributions in a canonical form with a base measure, natural parameters, and a log-partition function. For many families, such as the Beta distribution, the density can be written in more than one equivalent way, because constant offsets in the natural parameters can be moved into the base measure without changing the distribution. The team must fix a single convention for how to define the base measure so that the parameterization is unambiguous.


A: Move the leftover offset terms out of the natural parameters and into the base measure.


B: Set the base measure to the constant one and let the natural parameters carry the offset terms.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are standard, defensible conventions for fixing the non-uniqueness of exponential-family form. The choice depends on priorities such as interpretability, convenience, and compatibility. Neither is plainly inferior, and the context does not reveal which was chosen.", "case_for_1": "Moving offsets into the base measure gives the usual textbook form. For the Beta distribution, h(x)=1/(x(1-x)) and the natural parameters are α and β. This keeps the natural parameters as the clean, familiar parameters, makes sufficient statistics and natural parameters correspond directly, and matches common references for conjugacy and KL/Bregman computations.", "case_for_2": "A constant base measure of one is the simplest and most uniform rule. It applies the same way to every family, so no case-by-case judgment about which terms count as offsets is needed. It also makes the parameterization unambiguous, because the density is exp(η·T(x) − A(η)) with nothing else. This can simplify code and generic derivations, at the cost of shifted natural parameters such as α−1 and β−1."}}


### d3417e6a1c03

A research team derived closed-form expressions for the moments of a Gamma distribution and for the parameters that arise from moment matching, which is claimed to give the optimum when approximating a target distribution with a Gamma. Before relying on these derivations in later work, the team needed a way to establish that the derived moments and the moment-matching optimum are correct. They could choose between two approaches to establishing this correctness, differing in whether the result is checked against an independent numerical test or rests on the analytical derivation alone.


A: Derive the moments analytically from the moment generating function and its cumulant generating function, without any sampling or divergence checks.


B: Check the derived moments against sampling-based estimates visually, and compare empirical KL divergences for parameter pairs around the theoretical optimum.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible ways to establish correctness. Option 1 relies on a rigorous analytical derivation via the MGF/CGF, which is exact and cheap. Option 2 adds independent numerical verification of the moments and of the KL optimum, which can catch algebra or conceptual errors. The context states the difference as analytical-only versus an independent numerical check, so it does not make either option plainly inferior.", "case_for_1": "Gamma moments follow directly from the MGF/CGF, and the closed forms are standard and provable. Moment matching as the KL optimum within the exponential family is a known theorem. A proof is exact, general over all parameters, and avoids Monte Carlo noise and the ambiguity of visual comparison.", "case_for_2": "Derivations can contain subtle errors, such as parametrization mix-ups (shape/rate vs shape/scale) or the direction of the KL divergence. Sampling-based checks and KL comparisons around the claimed optimum independently test both the moments and the optimality claim. This is cheap insurance before relying on the results in later work."}}


### 881484cb0af5

A research team built quantitative models of how progress in machine learning unfolds, projecting whether the rate of progress will decelerate. Their models point toward a slowdown under the assumptions they encode. However, the models are simplified representations and may not capture all the drivers of ML progress, such as new paradigms, algorithmic breakthroughs, or changes in how resources are used. The team must decide how strongly to word the conclusion about whether a slowdown will occur.


A: State the conclusion firmly and assert that a slowdown is inevitable, treating the models' projections as sufficient grounds for the claim.


B: State the conclusion cautiously and decline to call a slowdown inevitable, since the models may not capture all the drivers of ML progress.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context stresses that the models are simplified and may miss drivers like new paradigms and breakthroughs. Calling a slowdown 'inevitable' on that basis overclaims, and the stated facts give no support for it. The cautious option is clearly better calibrated, and the firm option has no real counterweight beyond rhetorical punch.", "case_for_1": "A team might want a clear, headline-ready message to influence policy or planning, and a firm claim is easier to communicate. Still, 'inevitable' is not supported by simplified models, so this case is weak.", "case_for_2": "The models rest on encoded assumptions and may omit new paradigms, algorithmic breakthroughs, and shifts in resource use. Hedged wording reports the evidence accurately and keeps the team credible if the assumptions fail."}}


### b1e332844d86

A team has argued that speaking in a way optimized for efficiency is good for debaters. A critic has objected that this style suits judges who evaluate content, but does not carry over to persuasive speaking in general. The team must decide how broadly to state the claim, either limiting it to particular audiences and goals or keeping it as a general recommendation.


A: Keep the broad claim that efficiency optimization benefits speakers in general, treating the criticism as a minor caveat rather than a limit on the recommendation's scope.


B: Narrow the claim to say efficiency optimization helps debaters seeking content-based judging, while for those persuading general audiences it serves only as a starting point toward basic clarity.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The critic's objection is that efficiency-optimized speech suits content-focused judges but does not transfer to general persuasion. The stated facts give no support for the broad claim. Option 1 dismisses the objection as a 'minor caveat' without any counter-evidence. Option 2 accommodates the objection and still keeps a defensible recommendation for the debate context. The only thing Option 1 offers is a stronger, simpler claim, and that is not a real trade-off when the claim is likely overbroad.", "case_for_1": "A team might want a simple, memorable, general principle, and might think the critic is overstating things because clarity and efficiency do help most speakers to some degree. A broad claim is also easier to defend as a unified thesis. But it has to ignore the stated objection to do so, which makes this weak.", "case_for_2": "It scopes the claim to where the evidence applies (debaters facing content-evaluating judges), concedes the critic's valid point, and still gives guidance for general audiences. It is more accurate and more defensible, and it costs little."}}


### 3a304f6d20de

A research team is modeling how data accumulates over time on an online platform. A theoretical model of accumulation is available in two candidate forms: a simple exponential growth curve, and a more elaborate curve that multiplies a sigmoid term by an exponential term. They can test the candidate forms against real submission records from a large social media site. The team must decide which form of the theoretical model to accept as their description of data accumulation.


A: Accept the simple exponential model, because it describes data accumulation with fewer parameters and less complexity.


B: Accept the sigmoid-times-exponential model, because it fits real social media submission data better than the alternative forms.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "This is a standard parsimony versus fit trade-off. The context says the team can test the forms against real data but gives no results, so neither option is plainly inferior. The second option's claim of better fit is stated as a rationale and is not established by the context, so it does not leak the answer.", "case_for_1": "The exponential model has fewer parameters, which lowers the risk of overfitting, makes it easier to interpret, and gives it more generalizable predictions. If the fit gain from the elaborate form is marginal, or if a penalized criterion such as AIC or BIC favors the simpler model, parsimony justifies accepting it.", "case_for_2": "If the sigmoid-times-exponential curve fits real submission records substantially better, even after accounting for its extra parameters, it captures real saturation or adoption dynamics that pure exponential growth misses. Accepting the form the evidence supports is the empirically grounded choice."}}


### 67dd4f23948d

A research team is reviewing a published report from a policy think tank. The report estimates that the UK saves about £9.8 billion each year because smokers die prematurely, through lower spending on pensions, healthcare and social care. The team must decide how to treat this figure. They can take the estimate as a valid basis for their own work, or they can question its methods and assumptions and examine the question independently.


A: Reject the report's estimate of annual savings from premature smoking deaths as biased and run a separate analysis instead.


B: Accept the report's estimate of annual savings from premature smoking deaths as valid and use it without further analysis.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Accepting a published think-tank estimate saves time and resources, and it is reasonable if the report's methods are credible. Rejecting it and running an independent analysis is reasonable given that the figure is contested and politically sensitive. The context does not say which to choose, so the comparison is not an answer leak. The first option's wording, 'as biased', presumes bias, which is a mild framing issue. It does not make the option indefensible.", "case_for_1": "The figure is a politically sensitive estimate from a think tank, and it depends on contestable assumptions about discounting, counterfactual lifetime costs, and which costs and benefits are counted. If the team's own work relies heavily on it, independent scrutiny is prudent, and an independent analysis would let them control the methods and assumptions.", "case_for_2": "If resources are limited and the figure is only peripheral to the team's work, using a published estimate with transparent caveats is efficient. Duplicating a complex fiscal modelling exercise may add little. The team can cite the source and attribute the figure to it without endorsing it as definitive."}}


### af4f25edcc36

A research team has produced an estimate of whether a certain broad class of interventions has a net negative effect once all consequences are counted. The estimates feed on many uncertain inputs, with very wide plausible ranges, subjective judgments, and a methodology that likely skews the result in a known direction. In most modelled scenarios the net effect comes out negative, but the team knows the inputs are shaky and that unmodelled long-run effects could flip the sign. They must decide how strongly to state the conclusion in their write-up.


A: Treat the sign of the net effect as a case of complex cluelessness with fragile credences, make no confident net-negative claim, and flag the question for further investigation.


B: State a hedged best estimate that the net effect is negative in the vast majority of cases, and flag the high uncertainty, subjective error bars, and the direction of methodological bias.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible ways to communicate a fragile estimate. Option 1 is more epistemically conservative and withholds a confident claim. Option 2 reports the modelled result with explicit caveats. The context gives no sign that either is plainly wrong, and it does not reveal the recorded choice.", "case_for_1": "The inputs are shaky, the ranges are very wide, the methodology is biased in a known direction, and unmodelled long-run effects could flip the sign. A headline of 'vast majority negative' could be over-read and cause harm. Declaring cluelessness and calling for more investigation is honest and discourages premature action based on a fragile result.", "case_for_2": "The team did produce a best estimate, and most scenarios come out negative. Withholding it discards useful information. A hedged estimate with explicit caveats, error bars, and the bias direction lets readers update appropriately and make their own judgment. Calling it 'cluelessness' may be overly dismissive of real evidence, and decision-makers still have to act under uncertainty."}}


### c62eb0c5b58a

A group asked to take a public position on tobacco control must decide how to respond to the idea of prohibiting cigarettes altogether. Smoking is a leading cause of preventable disease and death. Prohibition would remove the main product at its source, but it raises concerns about enforcement, illicit markets, and public acceptance. Other measures are also available: progressively higher tobacco taxes, public education campaigns, and restrictions on smoking in public places. The group must choose which stance to back.


A: Decline an outright ban and support gradually increasing tobacco taxes alongside campaigns and smoke-free policies.


B: Endorse an outright ban on cigarette sales instead of relying on incremental tax, campaign and smoke-free measures.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible public health stances. Incremental taxes, campaigns, and smoke-free policies are evidence-backed and carry lower enforcement and illicit-market risk. An outright ban addresses the harm at its source and is a legitimate position for a group prioritizing ambition and endgame goals. The context lists the concerns but does not say which stance to take.", "case_for_1": "Gradual taxes, education, and smoke-free laws have strong evidence of reducing smoking. They avoid the enforcement burden, black markets, and public backlash that a ban would bring, and they are politically feasible and credible.", "case_for_2": "Smoking is a leading cause of preventable death, and incremental measures have left substantial smoking in place. A ban removes the product at its source and sets a clear endgame goal. A group taking a public position may reasonably favor a bold stance that shifts the debate, accepting implementation risks."}}


### a31835facf0a

A research team is defining a measure of productivity that includes a component attributing credit for outcomes to individual contributors or contributing factors. They recognize that credit assignment in this setting is inherently difficult: contributions interact, overlap and are not cleanly separable, and no agreed-upon rigorous method exists for measuring them. The team must decide how to treat this component in the definition. It can remain in the definition as an acknowledged imperfect element, or the team can make the definition depend on first obtaining a principled, rigorous solution to the attribution problem.


A: Derive a universally optimal, mathematically rigorous solution to credit assignment before finalizing the definition's attribution component.


B: Keep the attribution component in the definition as an acknowledged imperfect element and forgo any search for a rigorous measurement.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context states that no agreed-upon rigorous method exists and that contributions interact and are not cleanly separable. Option 1 requires a 'universally optimal, mathematically rigorous' solution before the definition can be finalized, which is practically unattainable and blocks progress. Option 2 is not a pure alternative either, because it adds 'forgo any search for a rigorous measurement,' which is an unnecessary extreme. Even so, Option 1 is plainly inferior as framed, since it sets an impossible precondition while Option 2 is workable.", "case_for_1": "Some would argue that a definition resting on an unprincipled component is unsound, so the team should insist on rigor first. That argument could justify a principled, bounded attempt such as axiomatic or Shapley-style approaches. It does not justify a 'universally optimal' solution as a precondition for finalizing the definition, so the case is weak.", "case_for_2": "Keeping the attribution component and openly acknowledging its limits lets the definition be finalized and used. The team can refine the component later as methods improve, and transparency about the limitation preserves honesty. The 'forgo any search' clause is overly rigid, but the core choice is still pragmatic and defensible."}}


### 85cfc0f57222

A research team has developed a new method and is writing up the results. Experiments show the method is competitive mainly in terms of speed: it runs much faster than alternatives, while its quality on other criteria is not clearly better and is often matched or exceeded by existing approaches. The draft's framing implicitly suggests broad usefulness. The team must decide how strongly to state the claims about the method's usefulness in the paper.


A: Restrict the usefulness claim to settings where very high speed is required, and state that other approaches are likely better elsewhere.


B: Present the method as broadly useful across settings, without limiting the claim to speed-critical cases or noting better alternatives.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "Under the stated facts, the method is competitive mainly on speed and often matched or exceeded on other criteria. Option 2 claims broad usefulness while omitting that limitation, which is not supported by the evidence and is an overclaim. Option 1 is accurate and still publishable, so no meaningful trade-off exists on scientific grounds.", "case_for_1": "The claim matches the evidence. It is honest, it is credible to reviewers, and it positions the method clearly for speed-critical use. It also avoids the risk of rejection or later correction for overclaiming.", "case_for_2": "The only argument is that broader framing may increase perceived impact and the chance of acceptance. This depends on overstating the results and is not defensible given the evidence."}}


### 25ec56b79297

A research team has completed a paper presenting a new method and is now preparing a conference poster to present the work. The paper itself discusses the method's shortcomings only indirectly, so a reader would need to infer them from the results and setup rather than finding them stated outright. The poster is a space where the first author can speak more informally and directly to visitors. The team must decide how explicitly the poster should communicate the method's limitations to visitors.


A: Keep the poster consistent with the paper by leaving the method's limitations implicit rather than stating them directly.


B: Add a dedicated section to the poster in the first author's candid voice that states the method's limitations explicitly.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context frames the poster as a space for informal, direct speech and notes that the paper only implies the limitations. Together these point toward explicit disclosure. Option 1 offers little beyond consistency with the paper and has no clear advantage, since an explicit limitations section does not conflict with the paper. The framing therefore tilts strongly toward option 2, though a weaker tradeoff exists around poster space and how the work is perceived.", "case_for_1": "Poster space is limited, and a limitations section could take room from the core contribution. Keeping the message uniform with the paper avoids any appearance of undermining the work. Visitors can raise limitations in conversation, and the first author can answer them there in person without putting them on the poster.", "case_for_2": "Stating limitations explicitly is more transparent and helps visitors judge the method accurately. It builds credibility, invites useful feedback, and uses the poster's informal setting to correct the paper's indirectness. Doing so does not contradict the paper."}}


### c4b274be3579

A research team is working on Inverse Classification, the task of generating or adjusting inputs so that a trained classifier assigns them to a desired class. They have already tried an LSTM-based approach to the problem and now must decide which generative model family to pursue next as the core of their method. The choice determines the architecture used to produce candidate inputs for the target class, and the team can commit to only one direction for the next stage of work.


A: Use LSTMs as the generative model for Inverse Classification.


B: Use conditional GANs as the generative model for Inverse Classification.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context says the team already tried an LSTM approach and must pick the next generative family. Option 1 means continuing with or refining LSTMs, and option 2 means switching to conditional GANs. Both are plausible, and neither is clearly inferior on the stated facts. The context does not say the LSTM attempt failed, so it does not point to either option.", "case_for_1": "The team already has LSTM infrastructure and experience, so continuing lowers risk and cost. LSTMs train stably and suit sequential or structured inputs such as text or time series. Likelihood-based training gives controllable generation, and the earlier attempt may only need refinement, not replacement.", "case_for_2": "Conditional GANs condition directly on the target class and can produce sharp, realistic samples, which matches the goal of generating inputs for a desired class. They suit continuous or image-like data and add diversity beyond what the LSTM approach gave. If the LSTM attempt fell short, switching families is a sensible exploration step."}}


### 50a312148a57

A research team has been writing papers that include a dedicated section openly describing the weaknesses, failure cases, and boundaries of their methods and results, rather than emphasizing only strengths. After using this approach, they must decide how to handle the practice in subsequent publications. One path is to treat the practice as a standing policy for future papers. The other is to return to the conventional style in which limitations are mentioned briefly or not highlighted. The decision weighs transparency and reader trust against the conventional expectations of how results are presented and received.


A: Return to the conventional presentation without a dedicated limitations section.


B: Keep including a dedicated honest-limitations section in all future papers.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Keeping a dedicated limitations section favors transparency and reader trust. Reverting to conventional style may be preferred under reviewer, competitive, or space pressures. The context states the tension neutrally and does not say which to choose, and the options are comparable.", "case_for_1": "Conventional presentation may fit venue norms, page limits, and reviewer expectations. Prominent weaknesses can sometimes be read as undermining the work, so reverting could improve acceptance odds and perceived impact. Limitations can still be mentioned briefly where relevant.", "case_for_2": "A dedicated limitations section builds credibility, helps readers judge validity and applicability, aids reproducibility, and reduces overclaiming. Many venues now encourage or require it, so a standing policy is low cost and consistent."}}


### 978cecc6cffd

A research team is using a pretrained conditional GAN generator whose input consists of a random noise vector and a class vector. They want to steer generated outputs by backpropagating gradient information from an external objective through the generator to its inputs. The generator weights stay frozen, so the team must decide which inputs receive gradient updates. The noise vector controls instance-level variation, while the class vector controls the semantic category. Updating only the class vector keeps the search space small and the sample's identity anchored to the noise, while updating the noise as well gives the optimization more freedom but risks drifting away from the intended distribution.


A: Update only the class vector by gradient descent while holding the noise vector fixed throughout optimization.


B: Update the class vector alone with the noise held fixed at first, then also optimize the noise vector in later optimization.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are reasonable ways to steer a frozen conditional generator. Option 1 is the conservative choice: a small search space, identity anchored to the noise, and little risk of leaving the data distribution. Option 2 is a staged schedule that begins the same way and later adds noise optimization for more expressiveness, at the cost of possible drift. The context presents this as a real trade-off and does not say which to pick.", "case_for_1": "Optimizing only the class vector keeps the search space small, preserves each sample's identity through the fixed noise, and avoids pushing the noise off the prior. This makes it more stable, simpler, and easier to interpret. It is a good fit when the goal is to modify a specific sample while staying in-distribution.", "case_for_2": "Starting with the class vector alone gets a stable coarse semantic shift. Adding noise optimization later gives the extra freedom needed to reach the external objective when class changes alone are not enough. The staged schedule limits early drift, and the noise updates can be regularized or limited to a few steps."}}


### c74dcc258417

A climate strategy team must decide what should anchor its approach to reducing emissions. One framing treats large corporations as the central adversary, with campaigns, pressure and confrontation aimed at major emitters as the main lever. The alternative framing moves away from singling out corporations and relies on market-based mechanisms, such as emissions caps with tradable permits, that change incentives across the whole economy. The team knows that emissions come from many sources, that corporate opposition has slowed past policy efforts, and that broad incentive mechanisms have a mixed record of political feasibility and effectiveness. It must choose which framing will serve as the core of its strategy.


A: Replace the corporation-focused framing with cap-and-trade style incentives as the strategy's core approach.


B: Keep the fight against large corporations as the central organizing principle of the climate strategy.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both framings are real strategic approaches, and the context gives balanced facts for each. Emissions are diffuse, which favors economy-wide incentives. Corporate opposition has slowed policy and market mechanisms have a mixed record, which supports either confrontation or caution about cap-and-trade. Neither option is clearly inferior, and the context does not reveal which one was chosen.", "case_for_1": "Emissions come from many sources, so a cap-and-trade mechanism changes incentives across the whole economy instead of targeting only the largest emitters. It avoids a purely adversarial stance that could harden opposition. It can also cut emissions at lower cost and has some precedent. A strategy built on one mechanism can be clearer and more scalable than campaigns against individual firms.", "case_for_2": "Corporate opposition has demonstrably blocked past policy, and broad incentive schemes have a mixed record on feasibility and effectiveness. Pressure campaigns on major emitters can produce concentrated, near-term results and build political power and public mobilization. They can also create the conditions under which any policy mechanism could pass. A concentrated set of big emitters makes targeting them an efficient lever."}}


### 57f8d94234c9

A research team is building a method for inverse classification, in which the input features of a trained classifier are modified through gradient-based optimization so that the predicted outcome changes to a desired one. The optimization must be run repeatedly over many instances and requires a first-order optimizer to update the feature values. The team must select the optimizer for this procedure, weighing a plain stochastic gradient approach against an adaptive-learning-rate method.


A: Use an adaptive-learning-rate optimizer as the optimizer for the inverse classification procedure.


B: Use plain stochastic gradient descent as the optimizer for the inverse classification procedure.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both optimizers are standard, defensible choices for gradient-based feature optimization, and the context names the trade-off without stating which to pick. Adaptive methods offer robustness to learning-rate choice and faster convergence. Plain SGD offers simplicity, predictability, and fewer hyperparameters.", "case_for_1": "Adaptive optimizers such as Adam adjust per-feature step sizes, which helps when features are on different scales or the loss surface is poorly conditioned. They need less learning-rate tuning when the procedure is run across many instances, and they often converge faster, which cuts compute.", "case_for_2": "Plain SGD is simple and has few hyperparameters. Its behavior is predictable, and it has no per-parameter state that must be reset for each instance. It tends to take smoother, more controlled steps, so the modified instance stays closer to the original, and results are easier to reproduce and analyze."}}


### 84065e101a07

An individual who spends roughly a third of each day asleep is deciding whether to spend time and money on choosing a new mattress. Available evidence suggests that no single mattress type is clearly better than the others for people in general, and individual preferences and body types vary widely. Sleep quality affects daily functioning and health, and a mattress is a relatively costly purchase that lasts for years. The person must decide whether a dedicated investigation into mattresses is worth the effort.


A: Research mattresses in depth, because choosing a suitable one can improve sleep quality.


B: Skip researching mattresses, because no mattress type is better than the others for people in general.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. The evidence says no mattress type is better for people in general, but also that individual preferences and body types vary widely. That variation supports personalized research (option 1). Option 2's reasoning is weaker, since 'no type is better in general' doesn't imply 'no type is better for me'. Even so, skipping in-depth research can be reasonable given limited time, a low expected payoff from research, and the option to test mattresses in a store or use a trial period. The context does not state which action to take.", "case_for_1": "Sleep takes about a third of life and affects health and functioning. A mattress is costly and lasts for years. Individual fit varies widely, so the lack of a universal best type makes personal evaluation more valuable, not less. Researching, for example by trying options and checking return policies, could meaningfully improve sleep.", "case_for_2": "If no type is reliably better, extensive research may have a low expected payoff. The person could buy a reasonably priced mattress with a good trial or return policy and adjust by experience. This saves time and avoids analysis paralysis, and the cost of a mismatch is limited if returns are possible."}}


### b4cd37ad20d0

After purchasing a new mattress, a person noticed an apparent improvement in their condition, such as better sleep or less discomfort. Other circumstances changed over the same period and were not controlled, and no comparison or blinded measurement was available. The question is how to interpret the observed improvement and how much of it to attribute to the mattress.


A: Credit the mattress with part of the improvement and state that uncontrolled confounders prevent isolating its effect.


B: Attribute the entire improvement to the mattress and treat the other concurrent changes as irrelevant.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context states that other circumstances changed and were uncontrolled, with no comparison or blinding. Option 2 attributes the whole improvement to the mattress and dismisses the confounders as irrelevant, which is unsupported by the stated facts. Option 1 acknowledges partial credit and the confounding. No plausible priority or resource trade-off makes Option 2 defensible as an interpretation of the evidence.", "case_for_1": "It matches the evidence: the mattress plausibly contributed, but concurrent changes and the lack of controls or blinding prevent isolating its effect. Giving partial credit with a stated caveat is calibrated and honest.", "case_for_2": "The only argument is pragmatic: if the person just wants to justify the purchase or has strong prior reasons to believe mattresses matter, a simple attribution is convenient. But that does not hold up as an interpretation under the stated confounding, so no defensible case exists."}}


### 769de52252ae

A research team is tuning the size of an added noise parameter in an experiment and has swept a range of noise sizes. One noise size gave the highest accuracy of those tried, but that best accuracy is modest in absolute terms and is not clearly satisfactory for the intended purpose. The team must decide how to treat this best-performing setting: whether to accept it as the result, or to treat it as inadequate and continue exploring.


A: Accept the best-performing noise size as optimal, while judging its modest accuracy to be too poor for the purpose.


B: Reject the best-performing noise size as inadequate and continue searching by testing a different set of noise sizes.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["incoherent"], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "incoherent", "reason": "Option 1 is internally contradictory: it says to accept the best noise size as optimal while also judging its accuracy too poor for the purpose. The context frames the decision as accept vs. continue exploring, but Option 1 combines acceptance with a judgment of inadequacy, so it does not describe a coherent action. Option 2 is clear, but the pair cannot be compared as written.", "case_for_1": "Charitable reading: the best size is optimal within the swept range (a local, descriptive fact) and gets reported as the result, with a caveat that accuracy is poor. But that is reporting a limitation, not a distinct decision, and judging the accuracy 'too poor for the purpose' undercuts accepting it.", "case_for_2": "The best accuracy is modest and not clearly satisfactory, so extending or changing the sweep (the optimum may lie outside the range tried, or noise may not be the right lever) is a reasonable next step. This is a coherent and defensible choice."}}


### 9e4f09634e05

An individual tracking his own physiology with a wearable recovery-scoring device compared its daily recovery readings against his subjective sense of how recovered he felt. On most days the two agreed, but on some days they diverged: the device indicated poor or good recovery while he felt the opposite. He had to decide how to interpret these divergent cases. One possibility is that the device's reading shaped his expectations and thereby influenced how he felt or performed, so the discrepancy reflects expectation rather than physiology. Another is that the device captured real physiological state that his own perception missed, so its readings carry information beyond his intuition.


A: Conclude that the device's readings were right more often than his intuition and that the divergence is not a self-fulfilling prophecy.


B: Conclude that the divergence is a self-fulfilling prophecy produced by expecting to feel tired after seeing the device's reading.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 9, "votes": ["b", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are competing interpretations of the same divergence, and the stated facts do not settle which is right. Each is a plausible hypothesis for a self-tracker. The wording of the first option is a bit overreaching, but that does not make either one defective.", "case_for_1": "Wearables measure signals such as HRV, resting heart rate, and sleep that people perceive poorly. Subjective feelings of recovery are noisy and can be influenced by mood or stress. If the device's readings predict later performance or illness better than his intuition does, then the divergence reflects real physiology and not expectation.", "case_for_2": "He sees the score before or while judging how he feels, so the readout could anchor his expectations. Placebo and nocebo effects are well documented, and a poor score could make him feel tired or perform worse. The fact that the two agree on most days and diverge on only a few is consistent with a score-driven expectation effect. Without blinding, expectation is a defensible explanation."}}


### f178e7d20972

A research team has completed an exploratory study of a new approach and obtained results that look encouraging but come from a limited set of experiments. They must decide how strongly to word the claims in their write-up. The wording can range from a strong statement that the approach clearly works to a more restrained statement about what the evidence supports.


A: Claim clear success for the approach and present the results as firm evidence that it works.


B: Make only cautious claims about feasibility and acknowledge the exploratory nature of the work.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says the results are encouraging but come from a limited set of exploratory experiments. Under those facts, presenting them as firm evidence that the approach clearly works is overclaiming. Cautious claims about feasibility match the evidence and are the standard norm of scientific reporting. The strong claim has no real offsetting benefit beyond possible hype or publicity, and it risks credibility and later retraction or correction. This is not a balanced trade-off.", "case_for_1": "The strongest case is strategic: bold claims may attract attention, funding, or priority in a competitive field, and the results do look encouraging. Even so, this rests on rhetoric rather than on the evidence, so it is hard to defend as a research-quality choice.", "case_for_2": "Cautious wording matches the limited, exploratory evidence, preserves credibility, and invites replication and follow-up. It still communicates the promising signal, so it loses little. It also avoids misleading readers and reduces the risk of having to walk back claims later."}}


### 24ca5cf90610

A research team wants to use the Laplace approximation to obtain tractable Gaussian approximations of distributions from the exponential family. For many of these distributions, a Gaussian fitted directly around the mode of the density in its native parameterization has problems: the Gaussian's support does not match the domain of the variable (for example, a positive or bounded quantity), the curvature at the mode can be undefined or degenerate, or the resulting Gaussian fits the true density poorly. The team must decide how to construct the Gaussian approximation so that it is usable across this family of distributions.


A: Apply a variable transformation before the Laplace approximation, fit the Gaussian in the transformed space, and map the result back to the original space.


B: Fit the Laplace approximation directly in the original parameter space, placing the Gaussian around the mode of the untransformed density.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context lists three failures of the direct approach: support mismatch, undefined or degenerate curvature at the mode, and poor fit. These are the problems the team needs to solve. Option 2 is the direct approach with those exact failures, so it cannot meet the stated goal of being usable across the family. Option 1, a transformation, addresses all three. Option 2 has little to offer beyond simplicity, and that is not a meaningful trade-off here. The context is also framed so that the transformation is the obvious answer.", "case_for_1": "A transformation, such as log for positive variables or logit for bounded ones, makes the Gaussian's support match the domain. It usually gives a well-defined mode with finite curvature and often a better fit. It works across the whole family and is a standard technique.", "case_for_2": "It is simpler. It needs no Jacobian and no back-mapping, and the result stays in the native parameterization. It works acceptably for distributions that are already near-Gaussian on an unbounded domain. However, the context says this approach has the problems the team must avoid, so it is hard to defend as a general method."}}


### 9e6263e28da9

A team needs to map Gaussian-distributed quantities onto Dirichlet or Beta distributions (and back) inside probabilistic models, a task that must be done many times and cheaply. A closed-form analytic approximation exists that matches the modes and curvature of the two distributions. It is very fast, but its error is fixed by construction and cannot be reduced by spending more compute. For example, the approximated Beta density goes to zero at the edges of the domain, which deviates from the true shape when parameters are small. The team must decide how to handle this limitation: either keep the fast closed-form mapping with its fixed error, or use alternative methods that can reach lower error by spending more runtime.


A: Use the closed-form mapping and accept its fixed approximation error in exchange for speed.


B: Use iterative methods whose approximation error decreases as more runtime is spent.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. The closed-form mapping gives speed and predictability, which matters because the task runs many times and must be cheap. Iterative methods can reach lower error, which matters most when parameters are small and the closed form deviates, for example when the Beta density goes to zero at the edges. The context states the limitation but does not say which option to pick.", "case_for_1": "The mapping is called many times and must be cheap. The closed form is very fast and deterministic, with no convergence tuning. The error may be tolerable in the regime of interest, such as moderate parameters, and it is unlikely to dominate the other errors in the model. Fixed, known error is easy to reason about.", "case_for_2": "When parameters are small, the closed form distorts the shape, and spending more compute cannot fix it. Iterative methods let the team trade runtime against accuracy and reach lower error where it matters. They can also be used selectively, only where the closed form performs poorly, so accuracy is not capped by construction."}}


### e9eaa284aef1

A research team evaluates a model that combines a linear model of coregionalization with a Gaussian process (LM+GP) on an experiment modeling currency exchange rates, where the target is a time-varying covariance matrix with an inverse Wishart structure. The LM+GP construction approximates the full process using a finite-dimensional linear projection of the Gaussian process, so some approximation loss is expected. For this experiment the true (co-)variance is known, including the quantities relating to the euro. The team must decide how to judge the quality of this approximation and present evidence about the loss it incurs.


A: Derive a theoretical bound on the posterior error caused by approximating the GP with a finite-dimensional linear projection as evidence of approximation loss.


B: Draw samples from LM+GP and compare them against the true (co-)variance with respect to the euro as empirical evidence of approximation loss.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible ways to assess approximation loss. A theoretical bound gives general guarantees, while an empirical comparison against the known true covariance gives concrete evidence on this experiment. The context says the truth is known, which favors the empirical route, but it does not make the theoretical bound unreasonable. It also does not reveal which option was chosen.", "case_for_1": "A bound on posterior error holds beyond this one dataset. It shows how the loss scales with projection dimension and can guide model design. It does not depend on the particular samples or on one currency, and a rigorous bound is a stronger kind of evidence than a single experiment.", "case_for_2": "The true (co-)variance for the euro is known, so sampling from LM+GP and comparing against it directly measures the loss in the actual setting. This is cheaper and more convincing for practitioners than a bound that may be loose or rest on unrealistic assumptions. It also exposes problems specific to the inverse Wishart structure."}}


### 9409139ae3c7

A research team is writing about why individuals differ in basic cognitive traits, the mental building blocks of thought and behavior. The standard account attributes these differences to genes (nature) and to upbringing and environment (nurture). The team has gathered observations suggesting that these two sources leave a substantial portion of variation unexplained, even among individuals with identical genes raised in similar environments. They propose that random events during brain development, such as stochastic variation in how neural circuits form, may supply a third source of variation. The evidence for this third source is suggestive but not conclusive. The team must decide how strongly to present this claim relative to the nature and nurture explanations.


A: Argue that chance events in brain development are a major third source of variation and that ignoring it is a colossal oversight in nature and nurture accounts.


B: Present chance events in brain development as a speculative factor that adds only a modest contribution to nature and nurture accounts.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible framings of suggestive but inconclusive evidence. The first is bolder and more provocative, and the second is more cautious. They differ in how strongly to claim the effect, which is a real trade-off between impact and epistemic caution.", "case_for_1": "The team observed a substantial unexplained portion of variation even among genetically identical individuals raised in similar environments. That residual is large, and the stochastic-development hypothesis is a natural explanation for it. A strong framing can shift the field's attention and spur research, and an argumentative piece may legitimately advocate a position. The wording 'colossal oversight' is rhetorical, but the underlying claim that the factor is major is supported by the size of the residual.", "case_for_2": "The evidence is suggestive but not conclusive, so calibrated language is warranted. Calling the factor speculative is accurate. Limiting it to a 'modest contribution' is a bit conservative given the large unexplained variance, but it protects credibility and avoids overclaiming. It still leaves room for follow-up work to strengthen the claim."}}


### 32718144bbe7

A writer has developed a theory about the basic mental building blocks that underlie thought. The theory rests on informal conversations and personal intuition, not on systematic study or formal evidence, and the writer has no established expertise in the field. The writer is preparing to publish it as an online post and must decide how strongly to present it to readers.


A: Present the post as a substantive theory and state its claims with confidence, without disclaimers.


B: Frame the post as food for thought rather than rigorous research and disclaim any expertise.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says the theory rests on informal conversations and intuition, with no systematic evidence and no expertise. Under those facts, presenting it confidently and with no disclaimers overstates its epistemic status and risks misleading readers. Framing it as food for thought is honest and still lets the writer share the idea. The first option has no meaningful offsetting benefit beyond persuasiveness or impact, which is not a legitimate trade-off against accuracy.", "case_for_1": "The writer might want the post to be punchy, persuasive and widely shared, since hedging can weaken engagement. Readers of online posts generally know that they are opinion pieces. Still, this does not justify confident claims with no disclaimers when the evidence is only intuition, so the case is weak.", "case_for_2": "This framing matches the actual evidence base and the writer's lack of expertise. It protects readers from being misled and protects the writer's credibility. It also invites discussion and feedback, and it still allows the idea to be published and refined."}}


### 3fc502a4fbc8

A person who navigates easily by orientation (keeping track of directions and heading) observed that many others navigate poorly this way. Until then, the person had assumed these others simply were not trying. Further observation raised the question of whether lack of effort was really the cause, or whether the difficulty came from something else about how those people think. The person had to decide how to interpret why others were bad at orientation-based navigation.


A: Reinterpret the difficulty as a difference in mental building blocks rather than as a lack of effort.


B: Keep attributing the difficulty to a lack of effort rather than to any difference in how people mentally represent space.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says further observation raised doubt that effort was the cause, and it gives no evidence supporting the effort explanation. Option 2 keeps the assumption the evidence has just undermined, and it excludes any cognitive-difference account outright. Option 1 fits the evidence and is the more open, reasonable interpretation. Option 2 also lacks a real resource or priority trade-off to justify it.", "case_for_1": "Observation suggested effort was not the cause. Skilled navigators often cannot imagine how others represent space, and people differ in spatial cognition, such as route-based versus orientation-based strategies. Reinterpreting is consistent with the evidence and leads to more accurate, more empathetic explanations.", "case_for_2": "Only a weak case exists. Effort is a simple, parsimonious hypothesis, and the evidence for cognitive differences may be anecdotal. Even so, rejecting any representational difference outright, after the person has seen evidence against the effort account, is not well supported."}}


### 711da16dab27

A team developed a fast approximate method (called LM) for modelling non-Gaussian data, such as multi-class outcomes, as an alternative to Gaussian process (GP) approaches. In their experiments, LM ran far more quickly than GP multi-class classification and Wishart process models, and its accuracy was close to or better than theirs. They had to decide how strongly to claim LM's speed and accuracy relative to these existing GP approaches, and whether to position it as a recommended default step ahead of full MCMC inference or as a more modest alternative.


A: Claim the proposed method is much faster and surprisingly accurate versus GP multi-class classification and Wishart processes, and recommend it as a baseline before MCMC.


B: Present the proposed method as only a modest alternative to GP multi-class classification, and keep GP-based approaches as the recommended standard for non-Gaussian data.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says LM was far faster and as accurate as or more accurate than GP multi-class classification and Wishart processes. Option 2 would keep GP methods as the recommended standard despite that evidence. It understates the findings and has no stated justification, such as a concern about generalization or robustness. Option 1 matches the reported results. The only real counterweight is general caution about overclaiming, but that does not make the second option well supported.", "case_for_1": "It follows the evidence: LM was much faster and as accurate or more accurate. Recommending it as a cheap baseline before MCMC is a practical use of that result and serves practitioners.", "case_for_2": "The best case is caution: the experiments may be limited in scope, and approximate methods can fail on other datasets. Even so, the context gives no such limitation, so keeping GP as the standard is weakly supported."}}


### 2f350b215cdb

A research team is analysing why nuclear power construction costs are so high. A widely repeated narrative holds that excessive safety regulation is the main reason costs rose, but the team has no direct evidence of its own that settles the question. They can either adopt this narrative as the explanation or test it first by looking for supporting evidence in sources written by both advocates and critics of nuclear power. The decision is how strongly to commit to the over-regulation explanation in their analysis.


A: Accept the over-regulation narrative as the main driver of nuclear's high costs and build the analysis on that premise directly.


B: Check pro- and anti-nuclear sources for corroboration, and describe over-regulation only as a plausible driver if little support turns up.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says the team has no direct evidence and that the narrative is only 'widely repeated'. Under those facts, building the whole analysis on an untested premise is plainly weaker than checking it against sources from both sides and calibrating the claim. Testing is cheap (a literature check) and gives a hedged fallback. Option 1's only real advantage is speed, which is not a meaningful trade-off for a research analysis whose central premise is unverified.", "case_for_1": "Strongest case is time pressure or a team that has good reason to trust the narrative. It would save effort and give a clear thesis. But the context says there is no evidence and gives no such constraint, so the case is weak.", "case_for_2": "Verifying with sources from both advocates and critics guards against adopting a popular but unsupported claim. The hedged wording stays honest if support is thin, and the analysis stays credible whichever way the evidence points."}}


### 1e0a8be21a28

A research team is assessing the economics of new nuclear power construction. Western projects have shown high and escalating costs, while reported figures from South Korea and China indicate much lower construction costs per unit of capacity. These lower figures could suggest that nuclear can be built cheaply. However, the figures come from state-influenced systems with different accounting practices, labor costs, supply chains and levels of transparency, so it is unclear whether they are comparable or transferable to other settings. The team must decide how to treat these figures when judging whether nuclear can be cheap.


A: Accept the South Korean and Chinese cost figures at face value as evidence that nuclear can be built cheaply.


B: Treat the South Korean and Chinese cost figures with caution, and do not accept them as evidence that nuclear can be cheap.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context stresses accounting differences, labor costs, supply chains and transparency, which make comparability doubtful. Option 1 ignores all of that and accepts the figures at face value. Option 2 is not a calibrated response either, since it dismisses the figures entirely, but it is far more defensible than uncritical acceptance. The comparison therefore has no meaningful trade-off.", "case_for_1": "Korea's reactors were built and operated, and the figures partly reflect real learning from standardized series builds. Rejecting them could be motivated skepticism that overlooks an existence proof. Even so, taking them at face value, with no adjustment, is hard to defend given the stated caveats.", "case_for_2": "Differences in accounting, labor costs, state influence and transparency limit how far the figures can be compared or transferred. Withholding acceptance is the prudent default for a team judging whether nuclear can be cheap in other settings. The weakness is that Option 2 says to reject the figures outright, where adjusting or discounting them would be more calibrated."}}


### 1fe2d769db7f

A research team is examining why nuclear power has become expensive and slow to build, and must decide how to treat the common view that the sector is held back mainly by a lack of technological innovation and that improved reactor designs are about to fix its cost and delivery problems. They know that past waves of promised advanced reactor technology have repeatedly failed to deliver the projected cost reductions, and that construction costs have stayed high despite many new designs. They must decide how much weight to give to present-day claims that better nuclear technology is imminent when explaining the sector's difficulties and judging its prospects.


A: Accept that nuclear power mainly needs more technological innovation, and treat new designs as the likely remedy.


B: Treat claims that better nuclear technology is imminent with greater skepticism, given the repeated record of unmet promises.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context states that past waves of promised advanced reactor technology repeatedly failed to deliver cost reductions and that costs stayed high despite many new designs. Under those facts, accepting that new designs are the likely remedy is plainly inferior to treating such claims skeptically. Option 1 ignores the stated evidence, and no real trade-off is described.", "case_for_1": "Option 1 could be argued on the grounds that some designs, such as SMRs and modular factory construction, differ in kind from past efforts. Optimism might also be useful for sustaining R&D funding. But the stated facts give no support for treating new designs as the likely remedy, so the case is weak.", "case_for_2": "The record of unmet promises is direct evidence that innovation claims are unreliable. Cost and delay problems may come from regulation, project management, supply chains, and financing rather than from reactor design, so skepticism is the better-calibrated stance for both explanation and prospects."}}


### a4e60b715566

A research team is assessing long-term energy system scenarios in which decarbonisation depends heavily on the falling costs of renewable technologies such as solar and wind. Many available model projections assume that historical learning rates, meaning the cost reductions seen per doubling of cumulative capacity, will persist into the future, and in these projections nuclear power plays only a small part. The team knows that learning rates have varied over time and across technologies, and that continued rapid cost declines are not guaranteed. They must decide how to treat the learning-rate assumption that underlies these projections when drawing conclusions about the future energy mix.


A: Treat learning rates as roughly constant and rely on model projections in which nuclear power plays only a minor role.


B: Treat learning rates as variable over time and build the analysis on that assumption instead of extrapolating past rates.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context states that learning rates have varied across time and technologies and that continued rapid declines are not guaranteed. Under those facts, assuming constant rates is plainly weaker than treating them as variable. The first option is a strawman. No stated resource or priority makes uncritical extrapolation the better choice. The context also frames the decision as how to treat the assumption when drawing conclusions, which leans toward the second option.", "case_for_1": "Constant learning rates are simple and transparent, they match much of the existing literature, and they keep results comparable with published projections. Still, the stated facts undercut this case, and it would only hold up as a baseline scenario, not as the basis for conclusions.", "case_for_2": "Treating learning rates as variable matches the stated evidence, avoids overconfident conclusions about nuclear's minor role, and allows sensitivity analysis and scenarios in which renewable cost declines slow."}}


### ab340f520d0d

A research team is analysing pathways for decarbonising an electricity system and must decide what to recommend about the existing fleet of nuclear power plants. These plants are ageing and approaching scheduled retirement. They already operate at low marginal cost and supply large amounts of low-carbon firm power. Building new nuclear capacity involves high upfront costs and a history of delays and overruns. The team must choose a recommendation for the existing fleet, within a broader assessment of how to reach deep emissions cuts at reasonable cost.


A: Recommend keeping the existing nuclear plants running as long as they can operate safely.


B: Recommend closing the existing nuclear plants as they reach their scheduled retirement.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are real policy stances. Life extension of existing nuclear is widely supported on cost and carbon grounds, but retiring plants on schedule can be defended given safety, ageing-asset, and reallocation concerns. The context leans toward extension by emphasizing low marginal cost and firm low-carbon power, yet it does not state the answer and does not make closure indefensible.", "case_for_1": "Existing plants are already built, have low marginal cost, and supply large amounts of firm low-carbon power. Replacing them would cost more and could raise emissions if gas fills the gap. Extending operation while it is safe is typically the cheapest route to deep decarbonisation.", "case_for_2": "Ageing plants may need costly refurbishment and carry rising safety, reliability, and outage risks. Waste and liability issues remain. Scheduled retirement gives planning certainty and frees grid access, capital, and policy attention for renewables, storage, and transmission, which may be cheaper and faster. If the system has enough alternative low-carbon capacity, closure is a defensible choice."}}


### 6700d1c24ceb

A research team has compared the size of differences in mental characteristics with the size of differences in physical characteristics across the groups it studied. The evidence suggests the two kinds of difference are of broadly similar magnitude, but the measures are not identical and the comparison is imprecise. The team must decide how strongly to word the claim about this comparison in its write-up: either as a definite statement that the two kinds of difference are equal in size, or as a more tentative statement about how their magnitudes relate.


A: State flatly that mental differences are equal in magnitude to physical differences.


B: Frame the magnitude comparison of mental and physical differences as tentative, not equal.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context states that the evidence shows only broadly similar magnitudes, that the measures are not identical, and that the comparison is imprecise. Under those facts, a flat claim of equality overstates the evidence and has no real justification. Option 2 is the calibrated wording. The only point in favor of Option 1 is rhetorical punch, which is not a research trade-off.", "case_for_1": "A definite statement is clearer and more memorable, and it could be defended as a rounded summary of 'broadly similar' results. Even so, it conflicts with the stated imprecision and non-identical measures, so no strong case exists.", "case_for_2": "Tentative wording matches the imprecise evidence and non-identical measures. It avoids overclaiming, stays accurate if later data shift the comparison, and protects the team's credibility."}}


### fdae880f4b27

A research team is building an inverse classification approach, in which a generative model produces inputs conditioned on class labels, instead of predicting labels from inputs. With a single network handling all classes, performance was acceptable on small datasets but degraded on larger datasets with more classes, because the latent space became less structured as the amount and diversity of data grew. The team must decide how to architect the model to contain this growing complexity.


A: Use a single large generative network shared across all classes, so that one network models every class.


B: Use a separate generative expert network for each class, so that every network models only one class.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context says a single shared network degraded on larger, more diverse datasets because the latent space lost structure, and the team must contain that growing complexity. Option 1 is the approach that already failed, and it is only scaled up. Option 2 addresses the stated cause directly. Per-class experts do carry costs: parameters and training scale linearly with class count, and the experts share no structure. Even so, the context gives no reason to expect that a larger single network would fix the degradation.", "case_for_1": "A single shared network is cheaper in parameters, trains once, and can share features across related classes. Greater capacity might delay the degradation. The context offers no evidence that this would solve it, so the case is weak.", "case_for_2": "Each expert models only one class, so latent-space structure cannot be disrupted by other classes' diversity. This isolates complexity and directly answers the stated failure mode. Experts can also be trained and added independently, though total cost grows with the number of classes."}}


### 7d8dba53b962

A research team is deciding how to divide a limited energy-innovation budget among competing low-carbon pathways. The goal is a reliable, affordable, low-emissions power system over the coming decades. Renewable generation and energy storage have seen steep cost declines and rapid deployment, but face questions about firm capacity, long-duration storage and integration. Nuclear power offers firm, dispatchable low-carbon output, but has a history of high costs, long construction times and a demanding regulatory environment. The team must choose which pathway gets the main priority and how the other is positioned relative to it.


A: Direct most of the budget to renewables and storage, and design nuclear to complement a grid dominated by renewables.


B: Direct most of the budget to nuclear by reforming regulation, building testing hubs and standardizing small reactor designs.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible strategies for a low-carbon grid. Option 1 relies on proven cost declines and rapid deployment, while accepting integration and firm-capacity risks. Option 2 targets firm, dispatchable power and addresses nuclear's cost and regulatory problems, but depends on reforms and standardization that are uncertain. The context does not favor either one.", "case_for_1": "Renewables and storage have the strongest record on cost declines and deployment speed, so a limited budget buys more near-term emissions cuts and affordability. Nuclear can fill the firm-capacity gaps that remain. This approach carries lower execution risk and builds on existing momentum.", "case_for_2": "Firm, dispatchable low-carbon power is hard to get from other sources, and nuclear's weaknesses (cost, delays, regulation) are partly institutional and may be fixable through reform, testing hubs and standardized small reactors. Renewables already attract large private investment and may need less public innovation money. Focusing the limited budget on the harder, underfunded problem could have higher marginal value for long-run reliability."}}


### 6b4097e0f10b

A team studying probabilistic models needs to explain why the probability density of the product of two independent random variables is not the same as the product of their individual probability density functions. The two variables have known densities, and the team wants a principled way to obtain the density of their product and show how it differs from the pointwise product of the densities.


A: Derive the density of the product by changing variables to the product and one factor, then integrating out the retained factor.


B: Obtain the density of the product by multiplying the two densities pointwise and renormalizing the result to integrate to one.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context asks for a principled way to get the density of the product and to show how it differs from the pointwise product of densities. Option 1 is the correct change-of-variables derivation. Option 2 (pointwise multiplication plus renormalization) is the very mistaken approach the team wants to explain away. It does not generally give the density of the product, so no real trade-off exists.", "case_for_1": "Setting W=XY and V=X, the joint density is f_X(v) f_Y(w/v)/|v|. Integrating out v gives f_W(w). This is exact and general, and it shows directly why the result differs from f_X(w) f_Y(w).", "case_for_2": "Essentially none. Pointwise multiplication and renormalization yields a density proportional to f_X f_Y, which is useful for combining likelihoods or experts. It is not the distribution of XY. It could serve only as a deliberately wrong counterexample, not as a method to obtain the density."}}


### d8d3c8671d15

A research team is preparing the empirical evaluation of a new method that is trained on a labeled subset of a larger dataset. They must decide the experimental regime in which to test it. The choice covers how many labeled examples per class to use and how the training points are chosen from the available pool. The method's behavior may depend on both the amount of labeled data and on which points are selected. The team must settle the scope of the evaluation before running the main experiments.


A: Focus the experiments on a low-data regime with very few examples per class, and compare random against clustering-based selection of training points.


B: Evaluate the method using only randomly selected training points, with no comparison against alternative selection strategies such as clustering-based selection.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible evaluation scopes. Option 1 studies a low-data regime and compares selection strategies. Option 2 uses random selection only, which gives a simpler and standard baseline. The context says behavior may depend on selection, which favors option 1, but that does not make option 2 plainly inferior. The options also differ in more than one respect (regime and selection comparison), but they remain comparable as evaluation scopes.", "case_for_1": "The context says behavior may depend on both the amount of labeled data and which points are selected. Comparing random against clustering-based selection in a low-data regime tests that dependence directly. Selection effects are also largest when labels are scarce, so this design is informative.", "case_for_2": "Random selection is the standard, unbiased protocol. It is cheaper and keeps the claim focused on the method itself, without confounding it with selection heuristics. It also avoids tailoring the evaluation to a regime where the method may do especially well, and results are easier to reproduce and compare with prior work."}}


### f769265d8b7b

A research team is evaluating a modular approach to neural network design. Their experiments use simple image-classification datasets, and the modular approach outperforms a standard neural network baseline in three of four tested scenarios. Because the datasets are simple, the results may not carry over to more complex settings. The team must decide how to frame and support the evidence for the modular approach in their write-up.


A: State the results as some evidence in favour of the approach, citing wins in three of four scenarios, and note that simple datasets may not reflect complex scenarios.


B: Measure modularity directly in MLPs on two image datasets across activation and dropout settings, and report how modular structure trades off against task performance.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Option 1 is a cheap, honest framing of existing results with a caveat. Option 2 adds new experiments that measure modularity directly and examine the modularity-performance trade-off. Both are defensible ways to support the evidence in the write-up, and they differ in cost, scope, and rigor. Neither is plainly inferior, and the context does not reveal which was chosen.", "case_for_1": "It matches the evidence actually in hand, claims no more than the data support, and discloses the main limitation. It needs no extra compute or time, so it suits a short write-up or a deadline. Calibrated language like 'some evidence' is good scientific practice.", "case_for_2": "Winning in 3 of 4 scenarios on simple datasets is weak evidence. Measuring modularity directly and showing how it trades off against performance would strengthen the claim and show whether modularity is what drives the gains. This addresses the generalization concern with substantive evidence instead of a caveat, and it gives a more informative contribution."}}


### 0854a2ee08ce

A research team has completed an analysis of what happens to old clothes when people donate them, and must now decide how to word the overall recommendation to the public. The findings carry some uncertainty about their correctness and generalisability. The team must choose between a recommendation that endorses donation, with its validity tied to the research being correct, and a recommendation that advises against donating at all.


A: Recommend that everyone donate old clothes, conditional on the research being correct.


B: Recommend that everyone refrain from donating old clothes, without conditions attached.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["incoherent", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "incoherent", "reason": "The context does not say what the research found, so the two recommendations cannot be compared on their merits. Option 1 is hedged and Option 2 is unconditional. That makes the choice a mix of direction (donate vs. don't) and hedging (conditional vs. unconditional), which are different dimensions. Because the findings are uncertain, an unconditional recommendation against donating is hard to justify alongside a conditional one for donating. The options are therefore not a clean like-for-like pair.", "case_for_1": "The findings are uncertain and may not generalise, so a recommendation explicitly conditioned on the research being correct is honest and calibrated. Donation is also the conventional, low-risk default, and it may well be what the research supports.", "case_for_2": "If the research showed that donated clothes mostly end up as waste or harm local markets abroad, a clear and unqualified message to stop donating would be simple and actionable for the public. Hedging can dilute the message. However, this contradicts the stated uncertainty, so the case is weak."}}


### cc1952da2cc3

A research team is assessing the economic impact of donating second-hand clothing to lower-income regions where local textile and garment industries have declined. Public debate often links donated clothing directly to that decline, but the evidence is mixed and several factors operate at once. The team must decide how to frame the economic analysis and which kind of evidence to rely on in order to judge how much donated clothing actually affects local markets, workers and consumers.


A: Organize the analysis around three questions on the causes of textile decline, the effects on jobs, and the benefits to consumers, to gauge how donated clothing affects local markets.


B: Use trade-flow statistics, such as import values and the donor country's share of total used-clothing exports to the region, to gauge how much donated clothing affects local markets.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Option 1 sets a broad analytical framework (causes, jobs, consumer benefits), while Option 2 commits to a specific evidence type (trade-flow statistics). They are not perfectly parallel, but both are plausible ways to approach the stated decision of framing and evidence. Each has real strengths and limits, and neither is plainly inferior.", "case_for_1": "The debate involves multiple interacting factors and several stakeholder groups. A framework that separates causation, labor effects, and consumer welfare avoids attributing decline to donations by default, and it captures benefits as well as harms. It also leaves room to use varied evidence.", "case_for_2": "Trade-flow data is objective, quantifiable, and comparable across regions and over time. It shows how much donated or used clothing actually enters the market, which is a necessary first step for judging scale. It also avoids the speculation and anecdote that dominate the public debate."}}


### 89e4661aefcb

A researcher investigating the consequences of donating used clothing has reached the point of writing a final recommendation for the public. The evidence collected is incomplete and uncertain, and it may not apply equally across cultural settings. The decision is how strongly to state the conclusion: whether to give a firm, unqualified directive, or a recommendation that openly carries the limits of the evidence.


A: Recommend that everyone donate old clothes, noting cultural uncertainty.


B: Recommend clearly and firmly that people not donate old clothes.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["incoherent", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "incoherent", "reason": "The context frames the decision as firm/unqualified versus hedged, but the options differ in direction (donate vs. don't donate) as well as in strength. Option 1 is hedged and pro-donation; option 2 is firm and anti-donation. The two options therefore vary two things at once, and the stated evidence gives no basis for either direction. This makes a clean comparison on the stated axis impossible. The context also doesn't reveal which action was recorded.", "case_for_1": "Given incomplete, culturally variable evidence, a hedged recommendation is epistemically honest. Donation is a common, low-harm default, and caveats about cultural applicability fit the stated uncertainty.", "case_for_2": "If the researcher's investigation found harms such as undermining local textile markets, a clear directive is easier for the public to act on. Even so, it conflicts with the stated uncertainty, so the case is weak."}}


### 065a06a6b7a5

A research team examined the effects of a large inflow of secondhand clothing (SHC) on the textile sector of a single East African country. One study of that country's laid-off textile workers reported that most of them later found jobs in the secondhand clothing trade, and that these jobs paid higher earnings than their former textile jobs. The team had to decide how far to extend this finding. The evidence came from one country with its own labor market, its own scale of textile employment and its own import policies, and no comparable worker-level evidence was available from other countries in the region.


A: Accept the finding and extend it to other African countries as a general conclusion about displaced textile workers.


B: Accept the finding for the single country studied and withhold its extension to other countries until further evidence is available.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context stresses that the evidence comes from a single country with its own labor market, textile scale, and import policies, and that no comparable worker-level evidence exists elsewhere. Under those facts, generalizing to other African countries as a general conclusion is unsupported, while limiting the claim to the studied country is plainly warranted. There is no real trade-off, since the only benefit of option 1 is a broader headline claim, which is not justified.", "case_for_1": "A team might argue that the mechanism (displaced workers moving into the booming SHC trade) plausibly operates across the region, and a bolder claim could prompt policy attention. But with no corroborating evidence and explicit context-specific differences, this is weak.", "case_for_2": "It matches the evidence's scope, avoids overgeneralizing from one labor market, and leaves room to update when comparable data appear. It still accepts the finding for the studied country."}}


### 230ba036d4a3

A research team is studying the sharp decline of textile employment and output in a set of economies that coincided with a surge in second-hand clothing (SHC) imports. An earlier published structural model estimated that SHC imports account for about 39% of the textile decline. The model rests on simplifying assumptions, such as stylized demand substitution between new and used clothing and limited treatment of other concurrent factors like trade liberalization, competition from cheap new imports, and domestic cost conditions. The team must decide how to read this estimate: whether it supports the view that SHC are the leading driver of the decline, or whether it should be read as a rough indication about the size of the SHC contribution relative to the total decline.


A: Interpret the 39% estimate as a rough but useful sign that SHC imports are not the majority cause of the decline.


B: Interpret the 39% estimate as showing that SHC imports are the main cause of the textile decline.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "Under the stated facts, 39% is less than half and the model has acknowledged limitations. Reading it as showing SHC is 'the main cause' is not supported. The first option is also hedged with 'rough but useful', so it matches the context's cautious framing. The second option overreaches given both the number and the model's simplifying assumptions, and no meaningful trade-off justifies it.", "case_for_1": "A 39% share is below a majority, and the model's simplifications and omitted factors (trade liberalization, cheap new imports, domestic costs) call for a cautious reading. Treating the figure as a rough indication of magnitude fits this. The conclusion that SHC is not the majority cause is reasonable, though it is itself uncertain.", "case_for_2": "The only defense is that 39% could be the largest single factor if the other causes are individually smaller, so SHC might be the leading driver without being a majority. However, the option says 'the main cause' and 'showing', which overstates what a model with acknowledged omitted factors can establish. The case is weak."}}


### 549cecc116db

A research team is analyzing the cultural trade-off that arises when cheaper trade or media exchange gives people in a society access to foreign, especially Western, cultural goods, while the same access may erode local traditions and cultural practices. Gains from access include lower prices, wider variety and exposure to new ideas. Potential losses include a decline in the value of existing cultures and a loss of cultural diversity. The empirical evidence on how large each effect is remains limited and uncertain. The team must decide which side of the trade-off its overall assessment should lean toward.


A: Favor protection of existing local cultures as the better side of the trade-off, while giving the uncertainty little weight.


B: Favor cheap access to new culture as the better side of the trade-off, while openly acknowledging the uncertainty in that judgment.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The options differ in direction and in how they handle uncertainty. The context says the evidence is limited and uncertain. Option 1 pairs its lean with giving that uncertainty little weight, which is poorly justified. Option 2 pairs its lean with openly acknowledging the uncertainty, which fits the stated facts. The uncertainty-handling difference is not a real trade-off, so Option 1 is plainly inferior as written.", "case_for_1": "Protecting local culture can be defended on precautionary grounds, since cultural loss is hard to reverse. But that argument relies on taking uncertainty seriously, which this option explicitly declines to do, so the case is weak as worded.", "case_for_2": "Cheap access offers concrete, measurable benefits such as lower prices, more variety, and exposure to new ideas. Acknowledging the uncertainty is the calibrated way to hold a lean given the limited evidence."}}


### 8767ac1af90f

A research team is running out-of-distribution detection experiments that require a Gaussian distribution over a network's output logits, obtained by approximating the posterior over the network's weights. The experiments span small-scale image benchmarks and several larger networks and datasets. Computing the approximate posterior over all weights becomes very expensive as network size grows, so the team must choose how much of the network to treat probabilistically in order to keep the cost manageable on the larger models while still producing the logit-space Gaussian.


A: Apply a Laplace approximation to only the final layer for the larger-network experiments, and keep the full-network version for the small image benchmarks.


B: Apply a Laplace approximation to all weights of the network for every experiment, including the larger-network ones, without restricting to a subset of layers.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible. Option 1 uses a last-layer Laplace approximation on large networks, which is a standard way to keep costs manageable and still gives a Gaussian over logits. Option 2 uses a full-network Laplace approximation everywhere, which gives a more faithful posterior but costs far more. The context says the cost is a concern but does not say full-network Laplace is infeasible, so it does not dominate. Cost against fidelity and consistency is a real trade-off.", "case_for_1": "The context stresses that cost grows with network size and must stay manageable on the larger models. Last-layer Laplace is cheap and gives the logit-space Gaussian in closed form. It often performs well for OOD detection. Using the full-network version on small benchmarks keeps fidelity where that is affordable.", "case_for_2": "Treating all weights probabilistically gives the most faithful posterior and uses the same method in every experiment, so results are comparable across scales. If the team has enough compute, or uses structured approximations such as KFAC, it avoids the bias of a last-layer-only posterior. This matters when the research question is about the approximation itself."}}


### 9e8db833b781

A team evaluated the Laplace Bridge, a closed-form method that approximates the predictive distribution of a Bayesian neural network by mapping a Gaussian over logits to a Dirichlet distribution, avoiding Monte Carlo sampling at prediction time. The approach had been proposed as a cheap alternative to sampling-based prediction. The team examined how it performs relative to sampling in terms of predictive quality and computational cost, and noted that sampling-based prediction implementations have become considerably faster in practice. They had to decide what to conclude about whether the Laplace Bridge merits further research effort or practical adoption.


A: Advise readers to abandon the Laplace Bridge line of work, except for rare cases where prediction speed is critical.


B: Advise readers to use sampling-based prediction instead, since modern implementations of it have become fast enough.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options recommend sampling over the Laplace Bridge and differ mainly in scope. Option 1 concludes the research line should be abandoned, with an exception for speed-critical settings. Option 2 gives a practical adoption recommendation to use sampling. Both fit the stated facts: the Laplace Bridge's speed advantage has eroded, and its predictive quality was compared against sampling. Neither is plainly inferior, and the context does not reveal which was recorded.", "case_for_1": "It speaks directly to whether the research effort is merited, which is the question posed. It also keeps a niche where the closed-form speed advantage still matters, so it is more nuanced and avoids overclaiming that sampling is always adequate.", "case_for_2": "It gives a simple, actionable practitioner recommendation grounded in the stated fact that sampling implementations are now fast. It avoids making a broad claim to discontinue research and stays closer to what the evaluation measured, namely quality and cost."}}


### 612ea20016ef

A research team is writing up the results of a study and must decide how to set priorities among the competing demands of writing: factual accuracy, ease of understanding, and brevity. Space is limited and readers skim, so the pull toward short, strong statements is real. Compressing claims can make them sound more impressive or more certain than the evidence supports, and dense text can be hard to follow. The team needs to settle on a guiding rule for how to rank these goals and how strongly to state what the results show.


A: Rank brevity first, ahead of truthfulness and understandability, and keep statements of the results as short as possible.


B: Rank truthfulness first, then understandability, then brevity, and avoid overstating or misrepresenting the results.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "Option 1 ranks brevity above truthfulness in scientific reporting. The context itself warns that compression can overstate certainty. Option 2 is the standard research-integrity priority. No realistic trade-off makes sacrificing accuracy for brevity defensible, so Option 1 is a strawman.", "case_for_1": "Space limits and skimming readers favor short statements, and a very short abstract or headline may be needed. But ranking brevity above truthfulness and understandability is not defensible, since it invites misrepresentation.", "case_for_2": "Accuracy is the core obligation of scientific writing. Clarity comes next so readers can follow it correctly. Brevity is pursued only after those two are met, which avoids the overstatement risk the context describes."}}


### 1de8016871d7

A research team is preparing a paper reporting a new method or system and must decide how to structure the experiments that will support it. The work could plausibly offer several kinds of benefits, such as accuracy, efficiency, generality, or interpretability, and the experiments run so far do not clearly favor one as the main contribution. The team must choose between organizing the paper around one explicitly claimed value, with experiments designed specifically to demonstrate it, and presenting the work without singling out one value. The choice shapes which experiments, baselines and analyses are collected as evidence.


A: Pick one value for the paper to provide, stress it from the opening, and design the experiments as evidence that this value exists.


B: Write the paper without anchoring it to a single claimed value and let the experiments cover the work's benefits broadly.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are defensible strategies given that experiments don't clearly favor one contribution. A focused claim gives a clear narrative and targeted experiments and baselines. A broad presentation avoids overclaiming and shows the work's multiple benefits. The context neither states which to choose nor makes either option plainly inferior.", "case_for_1": "A single clear claim makes the paper easier for reviewers and readers to understand and evaluate. It guides the choice of baselines and ablations, and it makes the evidence more rigorous. Papers without a clear contribution are often criticized as unfocused. Choosing the value the team can best support is a sound way to sharpen the work.", "case_for_2": "Since the existing experiments do not clearly favor any one value, committing early risks overclaiming or picking the wrong value. Broad coverage reports honestly what the method offers, and it lets readers with different priorities find the benefits that matter to them. It also avoids building experiments to confirm a predetermined story."}}


### 74e3a47f42ca

A research team compared a method referred to as the LB against alternatives, including sampling, in timing experiments. The results showed a speed/accuracy trade-off: the LB ran faster but with a small, consistent drop in output quality. The team had to decide how strongly to recommend the LB to readers given this trade-off.


A: Recommend sampling over the LB as the default choice, treating the LB's speed gains as not worth its quality loss.


B: Recommend the LB only when maximizing speed is the goal and a small, fixed quality drop is acceptable.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context describes a real speed/accuracy trade-off: the LB is faster but with a small, consistent quality drop. Recommending sampling as the default and recommending the LB conditionally are both defensible ways to weigh that. The context does not reveal which recommendation the team made.", "case_for_1": "If readers mostly care about output quality, a small but consistent loss is a systematic cost, so sampling is the safer default. Speed gains matter less when the drop applies to every use. A conservative default also protects readers who skip the caveats.", "case_for_2": "The trade-off is small and predictable, so the LB suits latency- or throughput-bound uses. Conditioning the recommendation on speed priority and acceptable quality loss reflects the evidence without overstating either side. It gives readers a decision rule rather than a blanket verdict."}}


### 5892c25fb2e8

A researcher has a long-term goal of making Bayesian machine learning faster. Time and attention are limited, so each new project competes with the others for the same hours. Many appealing project ideas keep arising, and some of them are intellectually engaging but do not clearly advance that central goal. The researcher must decide on what basis to select which projects to start.


A: Decline any project that does not advance the core goal of faster Bayesian machine learning, however interesting it is.


B: Pursue interesting projects even when they are unrelated to the core goal of faster Bayesian machine learning.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both are real project-selection policies. Strict focus protects a limited time budget for the long-term goal. Pursuing interesting work trades some focus for motivation, serendipity, and exploration. The context does not state which policy to adopt, although it does frame off-goal projects as distractions.", "case_for_1": "Time is limited and projects compete for the same hours. A strict filter makes the most of those hours for the central goal and builds depth and a coherent track record in fast Bayesian ML. It also avoids the opportunity cost of scattered efforts.", "case_for_2": "Interest drives sustained motivation and creativity. Unrelated projects can build skills, produce unexpected cross-pollination, or open better research directions, and a researcher who is too narrow risks burnout or missing breakthroughs. A policy of following interest can be rational when the long-term goal is uncertain and exploration has option value."}}


### 37e0922e3656

A research team is starting a new project whose central idea carries some critical weakness, meaning a finding that, if it emerged, would show the project cannot work. The team has to decide what kind of evidence to prioritise in the early phase. Early work can either steer toward the parts of the problem where the idea looks promising and progress is easy to show, or it can go straight at the part most likely to expose a fatal flaw. Resources in the early phase are limited, and the team has seen from earlier experience how a fundamental problem left unexamined can surface late and cost a great deal of effort.


A: Target the most likely fatal weakness of the project from the start and investigate it first, before building on the idea.


B: Steer early work toward the promising, easily demonstrated parts of the project and leave the most likely fatal weakness for later.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context states that a fundamental problem left unexamined can surface late and cost a great deal of effort. It also frames the weakness as one that would show the project cannot work. Under these facts, option 1 (test the fatal weakness first) clearly wins. Option 2 has only weak advantages, such as easy demonstrations and early momentum, and the context gives no reason that these outweigh the risk of a late-surfacing flaw. The framing also leans toward option 1 through the team's earlier experience.", "case_for_1": "Falsification-first is the standard risk-reduction approach. With limited resources, finding a fatal flaw early avoids sunk costs, and the team's past experience supports it. If the idea survives, everything built on it rests on firmer ground.", "case_for_2": "Early demonstrable wins could secure funding, morale, or stakeholder buy-in, and they might clarify the problem before the hard test is designed. However, the context gives no indication that these considerations apply, and they do not outweigh the stated cost of late discovery, so this case is weak."}}


### 8f90c488ae92

A PhD student is partway through a main doctoral project and keeps meeting interesting side projects that could be done alongside it. Some of these projects fall outside the direction of the thesis. Taking them on could broaden the student's experience and produce extra results, but it would also divide time and attention. The student must decide how to allocate effort between the main project and these opportunities.


A: Take on interesting side projects alongside the main PhD project even when they diverge from its trajectory.


B: Concentrate on the main PhD project and decline side projects that do not fit its trajectory.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are common, defensible strategies for a PhD student. The context states real benefits (breadth, extra results) and costs (divided time and attention) without favoring either. The right choice depends on thesis progress, advisor expectations, career goals, and the student's capacity.", "case_for_1": "Side projects build skills, collaborations, and publications, and they hedge against the main project stalling. They also help with career paths that value breadth, such as industry or a change of field. Early or mid-PhD students with a supportive advisor and enough slack can take them on without hurting the thesis.", "case_for_2": "Focusing protects time and attention for finishing the thesis on schedule, which is the main requirement for the degree and for funding. Depth and a coherent thesis story often matter more than scattered extra outputs. Declining off-trajectory projects avoids overcommitment and context-switching costs."}}


### 06916f0797ef

A research team must decide what kind of academic output to prioritize. Work that looks novel and flashy carries higher status and draws strong pressure toward it, but it is often harder to produce and less reliably useful. Simpler outputs, such as overview, benchmark or tutorial-style papers, can be produced in larger numbers and serve the community in a more practical way, but they are generally seen as less prestigious. The team must choose which kind of output to make its main focus.


A: Write fewer novel, flashy papers aimed at high-status venues instead of simple overview papers.


B: Write many simple overview, benchmark or tutorial-style papers instead of novel, flashy ones.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context presents a real tension between prestige and difficulty (novel work) and practical usefulness and volume (overview/benchmark/tutorial papers). Neither option is plainly inferior, and the context does not say which to choose. Its framing leans slightly toward simpler outputs, but it stops short of dictating the choice.", "case_for_1": "Novel work at high-status venues can advance careers, funding, and visibility, and can produce breakthroughs that overview papers cannot. A team with strong ideas, or one that needs prestige to secure grants or hire, could reasonably take on the higher risk.", "case_for_2": "Overview, benchmark, and tutorial papers can be produced reliably and in volume, and they are practically useful and often highly cited. They suit teams that prioritize community service, steady output, and lower risk."}}


### 531d401ed692

A research team is one week away from a conference submission deadline. Their paper still has major content gaps: the work is not yet complete enough to present a full, convincing contribution. Another conference with a later deadline is available as an alternative venue. The team must decide how to handle the remaining week, weighing the benefit of meeting the current deadline against the quality of the finished paper and the cost to the team of an intensive push.


A: Work through the final week on caffeine and little sleep to finish the paper for the current deadline.


B: Postpone the paper and submit it to a later conference instead of rushing to finish it for the current deadline.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given the stated facts. Crunching for the current deadline gets the paper out sooner, while postponing protects quality and team wellbeing. The context names the trade-off but does not say which to pick. The wording of option 1 is somewhat loaded, but it still describes a real choice.", "case_for_1": "The deadline is fixed and the team may be close enough to finish. Submitting now gets feedback and a publication sooner, and it avoids being scooped. Some teams accept a short, intense push for competitive or career reasons such as a graduation, grant, or job-market deadline. Reviewer feedback could also improve the paper even if it is rejected.", "case_for_2": "The paper has major content gaps, so one week of sleep-deprived work is unlikely to fix them and may produce a weak, error-prone submission. A later venue is available, so waiting costs little and allows a complete, convincing contribution. It also avoids burnout and protects the team's health and the paper's reputation."}}


### 7757c4b3006c

A research team is evaluating genetically modified (GM) crop plants and must decide how to treat the objections raised against them. Critics argue that transgenes could escape into wild or conventional relatives through cross-pollination, that inserted genes could mutate or behave unpredictably, and that widespread cultivation could reduce biodiversity and disturb surrounding ecosystems. Supporters point to the agronomic and economic benefits of GM crops and to the lack of conclusive, directly demonstrated harm. The team must decide how to weigh these environmental and safety objections in their overall assessment.


A: Accept the gene escape, mutation, biodiversity and ecosystem concerns as significant objections to GM plants.


B: Reject the gene escape, mutation, biodiversity and ecosystem concerns as unsupported objections to GM plants.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context says harms are not conclusively or directly demonstrated, but it also describes the objections as plausible mechanisms, such as cross-pollination, unpredictable gene behavior, and ecosystem disturbance. Option 2 calls them 'unsupported', which goes beyond 'lack of conclusive demonstrated harm'. Absence of conclusive evidence is not the same as the concerns being unsupported, since gene flow is well documented. Option 1 is a coarse binary but is more defensible. Option 2 is a blanket dismissal that the stated facts do not justify.", "case_for_1": "Gene flow via cross-pollination is a known biological mechanism, and ecological effects are hard to rule out. A precautionary assessment treats these as significant objections to be weighed and managed, even without demonstrated harm.", "case_for_2": "The strongest case is that no direct harm has been shown and the benefits are real, so the team could treat the concerns as speculative and not decision-relevant. However, calling them 'unsupported' overstates the evidence, because the mechanisms are plausible and gene flow is documented."}}


### 9ccb5a4a5781

A research team is reviewing the literature on how the risk of depression changes across the adult lifespan. The available studies give conflicting pictures. They agree with each other about risk in very old age, but they disagree about risk during working-age years. The team must decide how to interpret this conflicting evidence and what to conclude about the overall shape of the age trajectory.


A: Conclude that depression risk follows a U-shaped trajectory across age, with higher risk in youth and old age and lower risk in midlife.


B: Report that the studies agree on very old age but disagree on working age, leave the discrepancy unresolved, and request newer data.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "The context describes studies that agree on very old age but conflict on working-age risk. Option 1 commits to a U-shape, which is an interpretive synthesis and carries risk because the conflict is exactly about midlife. Option 2 reports the disagreement and requests more data, which is cautious. Both are defensible. The choice depends on how much the team values a decisive conclusion versus avoiding overreach.", "case_for_1": "Reviews are expected to synthesize. A U-shape is a well-known pattern in the literature, and the agreed old-age finding with elevated risk could support it. Pooling or weighting studies by quality and methods might justify a tentative U-shape, and a clear conclusion gives readers something usable.", "case_for_2": "The disagreement is about midlife, which determines the shape of the curve, so asserting a U-shape goes beyond what the conflicting evidence supports. Stating the agreement and the discrepancy honestly and asking for newer data avoids a premature conclusion and keeps the uncertainty visible."}}


### 00f1d5cea9fa

A person held a position in a disagreement over the role of private health insurance. In a follow-up discussion, the other party presented strong counterarguments to that position. The person had to decide how to interpret the disagreement in light of those arguments. The available considerations did not clearly settle the question by logic alone, and the person did not have systematic empirical evidence on the relevant outcomes.


A: Maintain the original position on private health insurance, treating the strong counterarguments as insufficient grounds to change it.


B: Conclude that the disagreement turns on empirical data currently lacking, and neither maintain nor reverse the original position.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible given the stated facts. The counterarguments are strong, but the considerations don't settle the question logically and there is no systematic empirical evidence. Maintaining the position is reasonable under uncertainty, and suspending judgment pending data is reasonable too. Neither option is plainly inferior, and the context does not reveal which one was chosen.", "case_for_1": "Strong counterarguments are not decisive when the question is not settled by logic or data. Holding a considered view absent compelling reason to change is rational, and it avoids abandoning a position under rhetorical pressure. Positions on health policy also rest on values, such as equity versus choice, that empirical gaps do not undermine.", "case_for_2": "The person lacks systematic evidence, and the counterarguments are strong. Honest calibration therefore suggests that confidence in the original position should drop and that the dispute depends on empirical outcomes. Suspending judgment while naming the missing data is epistemically humble and accurately describes where the disagreement lies."}}


### 891a0b642d13

A research team is reviewing the set-point (hedonic treadmill) theory of well-being, which holds that people adapt to major positive and negative life events and return to a stable baseline level of happiness. The team must decide how strongly to state this theory in their account. Available evidence shows substantial adaptation to many life events, but also notable individual differences in how people respond, evidence that some events (such as long-term unemployment or disability) produce lasting shifts in well-being, and baseline levels that appear to change for some people over time. The team must choose how to characterize the theory's claim about the stability of the baseline.


A: Conclude that the set-point is fixed and present the theory as a deterministic account of adaptation.


B: Conclude that the theory has some merit but present it as a softer, less deterministic account of adaptation.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context lists evidence against a fixed baseline: lasting shifts after long-term unemployment or disability, individual differences, and baselines that change over time. Option 1 (fixed, deterministic) contradicts this evidence. Option 2 matches it. No plausible priority makes overstating the theory the better choice under these facts.", "case_for_1": "Only a weak case: a strong, simple claim is clearer and easier to test or falsify, and adaptation is substantial in many cases. But the stated evidence directly contradicts 'fixed' and 'deterministic', so this is hard to defend.", "case_for_2": "It reflects the evidence accurately: substantial adaptation, but also variation, lasting shifts, and changing baselines. It keeps the theory's insight while acknowledging its limits, which is the calibrated choice."}}


### bc1e2adf2bbb

A review team is assessing the ethics and risks of genetic modification across living organisms. Having already weighed the benefits, harms and uncertainties for genetically modified plants, the team now turns to animals. The animal case involves additional considerations, including animal welfare, sentience, ecological effects of release, and less established evidence of benefit relative to the plant case. The team must decide how firmly to state its overall conclusion on genetically modifying animals, given that the balance of considerations is harder to judge and more uncertain here than for plants.


A: Conclude in favor of genetically modifying animals while stating that the weighing is harder and less certain than for plants.


B: Conclude against genetically modifying animals, stating that the risks and welfare concerns outweigh the benefits.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "valid_tradeoff", "reason": "Both options are defensible conclusions under the stated uncertainty. One leans favorable with hedging, the other leans precautionary and cautionary. The context states that the balance is harder to judge, but does not say which way it tips, and it does not reveal the recorded choice.", "case_for_1": "Animal GM has potential benefits such as disease resistance, medical models, and productivity. Case-by-case application with welfare safeguards can be justified. Acknowledging the greater uncertainty keeps the conclusion honest while still giving a usable verdict, consistent with the plant conclusion.", "case_for_2": "Sentience, welfare harms, and ecological release risks, combined with weaker evidence of benefit, support a precautionary stance. When harms are serious and benefits are unproven, concluding that risks outweigh benefits is reasonable, and it is stated firmly enough to guide policy."}}


### 6451927d6db7

A research team is summarizing evidence on the relationship between marriage and happiness. The available studies show that married people report higher happiness and life satisfaction than unmarried people. Some longitudinal findings suggest a modest rise in well-being around the time of marriage, but this often fades over time. Selection effects remain a concern, since happier people may be more likely to marry and stay married. Reverse causation and unmeasured confounding cannot be fully ruled out with the available designs. The team must decide how strongly to word its conclusion about whether marriage causes higher happiness.


A: State that marriage causally raises happiness as an established finding, without qualification.


B: Hedge the marriage findings and advise readers to treat the causal claim with caution.


Recorded choice: B


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "The context explicitly lists unresolved selection effects, reverse causation, confounding, and fading effects. Under these facts, asserting an unqualified established causal claim is not supported by the evidence and is plainly inferior to a hedged conclusion. No meaningful trade-off (e.g., cost or time) justifies overclaiming here.", "case_for_1": "Almost none. One could argue for a clear, simple message to the public or that the cross-sectional association is robust, but the stated facts directly undermine an unqualified, established causal claim.", "case_for_2": "It matches the evidence: a robust association, a modest and fading rise around marriage, and unresolved selection and confounding. Hedged wording preserves credibility, avoids misleading readers, and still reports the real association."}}


### 593c0c434116

A team is reviewing published research on whether optimism is linked to happiness and whether it causes it. Several papers report a positive association between optimism and happiness, and some of them describe the relationship as causal. The team knows that much of this evidence is observational or relies on self-report measures, and that these designs leave open questions about confounding and the direction of influence. They must decide how to treat the evidence when forming their own belief about the relationship.


A: Reject the optimism evidence as too methodologically weak to shift beliefs and rely on personal anecdote instead.


B: Accept the causal claims made in the papers and update beliefs to treat optimism as a cause of happiness.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated"], "agreement": 0, "votes": ["b", "b", "b", "b", "b", "b", "b", "b", "b", "b"], "quality": {"category": "dominated", "reason": "Both options are epistemically poor. Option 1 discards the evidence entirely and substitutes anecdote, which is weaker than flawed-but-informative research. Option 2 accepts causal claims despite the stated confounding and direction-of-influence problems. The sensible middle path (accept the association, stay uncertain about causation) is absent, so the pair is two extremes. Neither is a defensible stance under the stated facts, and no real trade-off exists between them.", "case_for_1": "Weak designs plus self-report bias could justify skepticism and a refusal to update on the causal claim. But replacing the evidence with personal anecdote is worse than the evidence it rejects, so the case is weak.", "case_for_2": "Several papers agree on the positive association, and some cite causal mechanisms, so a team might provisionally accept causation. This ignores the known design limits, so the case is weak."}}


### 48179ed1a6f0

A research team studying the relationship between marriage and subjective well-being faces conflicting findings in the literature. An earlier body of work, based on panel data tracking individuals before and after marriage, reported that life satisfaction rises around the time of marriage and then returns to each person's pre-marriage baseline within roughly two years, implying no lasting benefit. Later analyses, using longer follow-up periods and attention to differences in how people's satisfaction trajectories are modeled and who remains in the samples, suggest that married people maintain higher life satisfaction well beyond the initial period. The team must decide which characterization of the long-term effect of marriage on life satisfaction to accept.


A: Accept that marriage produces lasting long-term gains in life satisfaction that persist beyond the first two years.


B: Accept that marriage-related gains in life satisfaction fade back to baseline after roughly the first two years.


Recorded choice: A


Filter: {"status": "rejected", "reasons": ["dominated", "generic_agreement"], "agreement": 10, "votes": ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a"], "quality": {"category": "dominated", "reason": "The context frames the earlier adaptation finding as limited by short follow-up, trajectory modeling, and sample attrition. It frames later work as addressing those limits and finding lasting gains. Accepting the fade-to-baseline claim means choosing the findings with known methodological weaknesses over the ones that correct them. That is plainly inferior, so there is no real trade-off. The wording of the context also leans toward the first option, though it does not state the answer outright.", "case_for_1": "The later analyses used longer follow-up and handled trajectory modeling and selective attrition better, so their finding of sustained higher life satisfaction rests on stronger evidence and should be accepted.", "case_for_2": "The only argument is that the early panel studies had clean before-and-after designs that tracked the same individuals, and that later results might reflect selection into lasting marriages. The context presents these as weaknesses of the early work rather than strengths, so this case is weak."}}


## Pending