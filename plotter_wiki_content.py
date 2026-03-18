"""
plotter_wiki_content.py
=======================
Statistical reference content for Claude Plotter wiki.
All formulas use matplotlib mathtext syntax.
Citations reference section-level locations only.
"""

# VERIFICATION NOTE:
# All formulas are standard definitions appearing identically in
# Casella & Berger (2002) and Lehmann & Romano (2005).
# Section-level citations used (not theorem numbers).
# Report errors via GitHub Issues.

WIKI_SECTIONS = [

    # ─────────────────────────────────────────────────────────────────
    # SECTION 1: Independent Samples t-test (Welch's)
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Independent Samples t-test (Welch's)",
        "tags": ["scipy.stats.ttest_ind", "Parametric", "2 groups"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "The Welch t-test compares the means of two independent groups "
                    "without assuming equal population variances (the Behrens-Fisher "
                    "problem). It is the default two-sample t-test in GraphPad Prism "
                    "and in scipy (equal_var=False). Use when you cannot be certain "
                    "that the two groups share the same variance — which is almost "
                    "always the safer assumption."
                ),
            },
            {
                "heading": "Assumptions",
                "type": "numbered_list",
                "items": [
                    ("Independence", "Observations within and between groups are independent."),
                    ("Normality", "Each group is approximately normally distributed (or n is large enough for CLT)."),
                    ("Continuous outcome", "The response variable is measured on an interval or ratio scale."),
                    ("Unequal variances OK", "Welch's correction does NOT assume equal variances (unlike Student's t)."),
                ],
            },
            {
                "heading": "Student's pooled-variance t (equal variances assumed)",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$s_p = \sqrt{\frac{(n_1 - 1)s_1^2 + (n_2 - 1)s_2^2}{n_1 + n_2 - 2}}$",
                        "Pooled standard deviation — valid only when variances are equal.",
                    ),
                    (
                        r"$t_S = \frac{\bar{X}_1 - \bar{X}_2}{s_p\sqrt{\frac{1}{n_1} + \frac{1}{n_2}}}$",
                        "Student's t statistic with df = n1 + n2 - 2. Biased when variances differ.",
                    ),
                ],
                "source": "Casella & Berger §8.3",
            },
            {
                "heading": "Welch's t statistic",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$t_W = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{\frac{s_1^2}{n_1} + \frac{s_2^2}{n_2}}}$",
                        "Welch's t: difference of means divided by the standard error of the difference. Does not pool variances.",
                    ),
                ],
                "source": "Welch (1947)",
            },
            {
                "heading": "Welch–Satterthwaite degrees of freedom",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\nu \approx \frac{\left(\frac{s_1^2}{n_1} + \frac{s_2^2}{n_2}\right)^2}{\frac{(s_1^2/n_1)^2}{n_1-1} + \frac{(s_2^2/n_2)^2}{n_2-1}}$",
                        "Effective degrees of freedom. Usually non-integer; t-distribution is evaluated at this value.",
                    ),
                ],
                "source": "Satterthwaite (1946); Welch (1947)",
            },
            {
                "heading": "Distribution under H₀",
                "type": "text",
                "body": (
                    "Under H₀: μ₁ = μ₂, the Welch statistic tW follows a t-distribution "
                    "with ν degrees of freedom (Welch–Satterthwaite approximation). "
                    "The two-tailed p-value is p = 2·P(T > |tW|) where T ~ t(ν)."
                ),
            },
            {
                "heading": "Effect sizes",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$d = \frac{\bar{X}_1 - \bar{X}_2}{s_p}$",
                        "Cohen's d: standardised mean difference using pooled SD. Small ≈ 0.2, medium ≈ 0.5, large ≈ 0.8 (Cohen 1988 guidelines).",
                    ),
                    (
                        r"$g = d \cdot \left(1 - \frac{3}{4(n_1 + n_2 - 2) - 1}\right)$",
                        "Hedges' g: bias-corrected version of Cohen's d. Preferred for small samples.",
                    ),
                ],
                "source": "Cohen (1988); Hedges (1981)",
            },
            {
                "heading": "Confidence interval for the difference",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$(\bar{X}_1 - \bar{X}_2) \pm t_{\nu,\,\alpha/2} \cdot \sqrt{\frac{s_1^2}{n_1} + \frac{s_2^2}{n_2}}$",
                        "100(1−α)% CI for μ₁ − μ₂. Uses Welch–Satterthwaite ν and the corresponding t critical value.",
                    ),
                ],
                "source": "Casella & Berger §8.3",
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "scipy.stats.ttest_ind(a, b, equal_var=False) implements Welch's t-test. "
                    "GraphPad Prism calls this 'Unpaired t-test, Welch correction'. "
                    "Setting equal_var=True gives Student's pooled-variance t-test."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Welch, B.L. (1947). The generalization of Student's problem when several different population variances are involved. Biometrika, 34(1-2), 28-35.",
                    "Satterthwaite, F.E. (1946). An approximate distribution of estimates of variance components. Biometrics Bulletin, 2(6), 110-114.",
                    "Casella, G. & Berger, R.L. (2002). Statistical Inference, 2nd ed. §8.3.",
                    "Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences, 2nd ed.",
                    "Hedges, L.V. (1981). Distribution theory for Glass's estimator of effect size. Journal of Educational Statistics, 6(2), 107-128.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 2: Paired t-test
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Paired t-test",
        "tags": ["scipy.stats.ttest_rel", "Parametric", "Paired"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "The paired t-test compares two related measurements — "
                    "e.g., pre/post on the same subject, matched pairs, or "
                    "repeated measures with two time points. By working with "
                    "within-pair differences it removes between-subject variability, "
                    "giving greater power than an independent t-test when pairing "
                    "is effective."
                ),
            },
            {
                "heading": "Assumptions",
                "type": "numbered_list",
                "items": [
                    ("Paired observations", "Each observation in group 1 has a unique paired partner in group 2."),
                    ("Normality of differences", "The within-pair differences D_i = X_1i − X_2i are approximately normally distributed."),
                    ("Independence of pairs", "Pairs are independent of each other (not individual measurements)."),
                ],
            },
            {
                "heading": "Test statistic",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$D_i = X_{1i} - X_{2i}$",
                        "Within-pair difference for pair i.",
                    ),
                    (
                        r"$\bar{D} = \frac{1}{n}\sum_{i=1}^n D_i$",
                        "Mean of differences.",
                    ),
                    (
                        r"$s_D = \sqrt{\frac{\sum_{i=1}^n (D_i - \bar{D})^2}{n - 1}}$",
                        "Standard deviation of differences.",
                    ),
                    (
                        r"$t = \frac{\bar{D}}{s_D / \sqrt{n}}$",
                        "Paired t statistic. Under H₀: μ_D = 0, follows t(n−1).",
                    ),
                ],
                "source": "Casella & Berger §8.3",
            },
            {
                "heading": "Confidence interval for the mean difference",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\bar{D} \pm t_{n-1,\,\alpha/2} \cdot \frac{s_D}{\sqrt{n}}$",
                        "100(1−α)% CI for the population mean difference μ_D.",
                    ),
                ],
                "source": "Casella & Berger §8.3",
            },
            {
                "heading": "Effect size",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$d_z = \frac{\bar{D}}{s_D}$",
                        "Cohen's d_z for paired data: mean difference divided by SD of differences.",
                    ),
                ],
                "source": "Cohen (1988)",
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "scipy.stats.ttest_rel(a, b) computes the paired t-test. "
                    "It is equivalent to scipy.stats.ttest_1samp(a - b, 0). "
                    "GraphPad Prism calls this 'Paired t-test'."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Casella, G. & Berger, R.L. (2002). Statistical Inference, 2nd ed. §8.3.",
                    "Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences, 2nd ed.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 3: One-sample t-test
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "One-sample t-test",
        "tags": ["scipy.stats.ttest_1samp", "Parametric", "1 group"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "The one-sample t-test tests whether a sample mean differs "
                    "from a known or hypothesised population mean μ₀. "
                    "Common uses: testing whether a measurement differs from a "
                    "reference value (e.g., 100% control, 0 change, published norm)."
                ),
            },
            {
                "heading": "Assumptions",
                "type": "numbered_list",
                "items": [
                    ("Independence", "Observations are independently sampled."),
                    ("Normality", "The sample is drawn from a normal distribution (or n is large enough for CLT)."),
                    ("Known μ₀", "The hypothesised mean μ₀ is specified a priori, not estimated from the data."),
                ],
            },
            {
                "heading": "Test statistic",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$t = \frac{\bar{X} - \mu_0}{s / \sqrt{n}}$",
                        "Under H₀: μ = μ₀, this follows a t-distribution with n−1 degrees of freedom.",
                    ),
                ],
                "source": "Casella & Berger §8.3",
            },
            {
                "heading": "Confidence interval",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\bar{X} \pm t_{n-1,\,\alpha/2} \cdot \frac{s}{\sqrt{n}}$",
                        "100(1−α)% CI for the population mean μ.",
                    ),
                ],
                "source": "Casella & Berger §8.3",
            },
            {
                "heading": "Effect size",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$d = \frac{\bar{X} - \mu_0}{s}$",
                        "Cohen's d for one sample: standardised distance from the hypothesised value.",
                    ),
                ],
                "source": "Cohen (1988)",
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "scipy.stats.ttest_1samp(a, popmean) tests H₀: μ = popmean. "
                    "GraphPad Prism offers this under 'One-sample t test'."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Casella, G. & Berger, R.L. (2002). Statistical Inference, 2nd ed. §8.3.",
                    "Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences, 2nd ed.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 4: One-way ANOVA
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "One-way ANOVA",
        "tags": ["scipy.stats.f_oneway", "Parametric", "3+ groups"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "One-way ANOVA tests whether the means of k ≥ 2 independent groups "
                    "are equal. It partitions total variability into between-group "
                    "variance (signal) and within-group variance (noise). "
                    "A significant result only indicates that at least one group differs; "
                    "post-hoc tests identify which pairs differ."
                ),
            },
            {
                "heading": "Assumptions",
                "type": "numbered_list",
                "items": [
                    ("Independence", "Observations within and between groups are independent."),
                    ("Normality", "Each group is approximately normally distributed."),
                    ("Homoscedasticity", "Population variances are equal across groups (Welch ANOVA relaxes this)."),
                ],
            },
            {
                "heading": "Sum of squares partitioning",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$SS_{between} = \sum_{j=1}^k n_j(\bar{X}_j - \bar{X})^2$",
                        "Between-group SS: variability explained by group membership.",
                    ),
                    (
                        r"$SS_{within} = \sum_{j=1}^k \sum_{i=1}^{n_j} (X_{ij} - \bar{X}_j)^2$",
                        "Within-group SS: unexplained variability (error).",
                    ),
                    (
                        r"$SS_{total} = SS_{between} + SS_{within}$",
                        "Total SS = between + within.",
                    ),
                ],
                "source": "Casella & Berger §8.3",
            },
            {
                "heading": "F statistic",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$MS_{between} = \frac{SS_{between}}{k - 1}$",
                        "Mean square between groups (df = k−1).",
                    ),
                    (
                        r"$MS_{within} = \frac{SS_{within}}{N - k}$",
                        "Mean square within groups (df = N−k, where N = total observations).",
                    ),
                    (
                        r"$F = \frac{MS_{between}}{MS_{within}}$",
                        "Under H₀ (all means equal), F ~ F(k−1, N−k).",
                    ),
                ],
                "source": "Casella & Berger §8.3",
            },
            {
                "heading": "Effect sizes",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\eta^2 = \frac{SS_{between}}{SS_{total}}$",
                        "Eta-squared: proportion of total variance explained. Biased upward in small samples.",
                    ),
                    (
                        r"$\omega^2 = \frac{SS_{between} - (k-1)MS_{within}}{SS_{total} + MS_{within}}$",
                        "Omega-squared: bias-corrected effect size. Preferred over η². Small ≈ 0.01, medium ≈ 0.06, large ≈ 0.14.",
                    ),
                ],
                "source": "Cohen (1988); Casella & Berger §8.3",
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "scipy.stats.f_oneway(*groups) returns (F, p). "
                    "For unequal variances, consider Welch ANOVA (pingouin.welch_anova). "
                    "Follow significant results with post-hoc tests (Tukey, Dunnett, etc.)."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Casella, G. & Berger, R.L. (2002). Statistical Inference, 2nd ed. §8.3.",
                    "Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences, 2nd ed.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 5: Repeated Measures ANOVA
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Repeated Measures ANOVA",
        "tags": ["Parametric", "3+ groups", "Paired"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "Repeated measures ANOVA extends one-way ANOVA to designs where "
                    "the same subjects are measured across all k conditions. "
                    "It partitions within-subject variance from error, increasing "
                    "power compared to a between-subjects design when individual "
                    "differences are large."
                ),
            },
            {
                "heading": "Assumptions",
                "type": "numbered_list",
                "items": [
                    ("Normality", "The dependent variable is approximately normally distributed within each condition."),
                    ("Sphericity", "The variances of the pairwise difference scores are equal across all pairs of conditions (Mauchly's test checks this)."),
                    ("Independence", "Subjects are independent of each other."),
                ],
            },
            {
                "heading": "Sphericity and corrections",
                "type": "text",
                "body": (
                    "Sphericity is the repeated-measures analogue of homoscedasticity. "
                    "Violation inflates the Type I error rate. "
                    "Mauchly's test (W statistic) tests sphericity formally, though "
                    "it lacks power in small samples. When sphericity is violated:\n\n"
                    "• Greenhouse-Geisser correction (ε̂_GG): multiplies df by ε̂, "
                    "giving a more conservative F test. Recommended when ε̂ < 0.75.\n\n"
                    "• Huynh-Feldt correction (ε̂_HF): less conservative than GG. "
                    "Recommended when ε̂ ≥ 0.75.\n\n"
                    "• Multivariate approach (MANOVA): avoids sphericity assumption entirely "
                    "but requires more subjects than conditions."
                ),
            },
            {
                "heading": "F statistic (sphericity assumed)",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$F = \frac{MS_{conditions}}{MS_{error}}$",
                        "With df_conditions = k−1 and df_error = (k−1)(n−1), where n = subjects.",
                    ),
                ],
            },
            {
                "heading": "Effect size",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\eta_p^2 = \frac{SS_{conditions}}{SS_{conditions} + SS_{error}}$",
                        "Partial eta-squared for repeated measures: proportion of variance attributable to the within-subjects factor.",
                    ),
                ],
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "Python: pingouin.rm_anova() provides repeated measures ANOVA with "
                    "sphericity correction. R: ez::ezANOVA(), afex::aov_ez(). "
                    "GraphPad Prism: 'Repeated measures one-way ANOVA'."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Casella, G. & Berger, R.L. (2002). Statistical Inference, 2nd ed. §8.3.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 6: Two-way ANOVA
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Two-way ANOVA",
        "tags": ["Parametric", "Factorial"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "Two-way ANOVA tests the effects of two categorical factors (A and B) "
                    "and their interaction (A×B) on a continuous outcome. "
                    "The interaction term reveals whether the effect of one factor "
                    "depends on the level of the other."
                ),
            },
            {
                "heading": "Assumptions",
                "type": "numbered_list",
                "items": [
                    ("Independence", "Observations are independent."),
                    ("Normality", "Residuals are approximately normally distributed."),
                    ("Homoscedasticity", "Variance is equal across all cells of the factorial design."),
                    ("Balanced design", "Equal cell sizes simplify interpretation; unbalanced designs require careful choice of SS type."),
                ],
            },
            {
                "heading": "F statistics",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$F_A = \frac{MS_A}{MS_{error}}$",
                        "F for factor A (main effect).",
                    ),
                    (
                        r"$F_B = \frac{MS_B}{MS_{error}}$",
                        "F for factor B (main effect).",
                    ),
                    (
                        r"$F_{A \times B} = \frac{MS_{A \times B}}{MS_{error}}$",
                        "F for the A×B interaction. Significant interaction means main effects should be interpreted with caution.",
                    ),
                ],
                "source": "Casella & Berger §8.3",
            },
            {
                "heading": "Type I / II / III sums of squares",
                "type": "text",
                "body": (
                    "Type I SS (sequential): each effect is adjusted only for effects "
                    "entered before it in the model. Order-dependent; rarely appropriate.\n\n"
                    "Type II SS: each main effect adjusted for all other main effects, "
                    "but not for interactions. Appropriate when the interaction is absent.\n\n"
                    "Type III SS (partial): each effect adjusted for all other effects "
                    "including interactions. Default in most software; appropriate when "
                    "the design is unbalanced or interactions are present."
                ),
            },
            {
                "heading": "Effect size",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\eta_p^2 = \frac{SS_{effect}}{SS_{effect} + SS_{error}}$",
                        "Partial eta-squared: effect SS as a proportion of effect SS + error SS. Does not sum to 1 across effects.",
                    ),
                ],
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "Python: statsmodels.formula.api.ols() with anova_lm(type=3). "
                    "pingouin.anova() for balanced designs. "
                    "GraphPad Prism: 'Two-way ANOVA'."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Casella, G. & Berger, R.L. (2002). Statistical Inference, 2nd ed. §8.3.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 7: Mann-Whitney U
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Mann-Whitney U Test",
        "tags": ["scipy.stats.mannwhitneyu", "Non-parametric", "2 groups"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "The Mann-Whitney U test (also called Wilcoxon rank-sum test) "
                    "is the non-parametric alternative to the independent t-test. "
                    "It tests whether observations from one group tend to have "
                    "larger values than observations from the other group "
                    "(stochastic dominance). It does not require normality."
                ),
            },
            {
                "heading": "Assumptions",
                "type": "numbered_list",
                "items": [
                    ("Independence", "Observations within and between groups are independent."),
                    ("Ordinal scale", "The outcome is at least ordinal (can be ranked)."),
                    ("Continuous distribution", "For the Wilcoxon form of the hypothesis (shift model), distributions should be continuous and similarly shaped."),
                ],
            },
            {
                "heading": "U statistic",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$U_1 = n_1 n_2 + \frac{n_1(n_1+1)}{2} - R_1$",
                        "U for group 1, where R₁ is the sum of ranks assigned to group 1 after jointly ranking both groups.",
                    ),
                    (
                        r"$U_2 = n_1 n_2 - U_1$",
                        "U for group 2. The test statistic is U = min(U₁, U₂).",
                    ),
                ],
                "source": "Mann & Whitney (1947)",
            },
            {
                "heading": "Effect size: rank-biserial correlation",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$r_{rb} = \frac{U_1 - U_2}{n_1 \cdot n_2} = 1 - \frac{2U}{n_1 n_2}$",
                        "Rank-biserial correlation: ranges from −1 to +1. Interpreted like Cohen's d guidelines: |r| ≈ 0.1 small, 0.3 medium, 0.5 large.",
                    ),
                ],
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "scipy.stats.mannwhitneyu(x, y, alternative='two-sided') returns "
                    "the U statistic and p-value. For large samples, uses a normal "
                    "approximation with continuity correction. "
                    "GraphPad Prism calls this 'Mann-Whitney test'."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Mann, H.B. & Whitney, D.R. (1947). On a test of whether one of two random variables is stochastically larger than the other. Annals of Mathematical Statistics, 18(1), 50-60.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 8: Wilcoxon Signed-Rank
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Wilcoxon Signed-Rank Test",
        "tags": ["scipy.stats.wilcoxon", "Non-parametric", "Paired"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "The Wilcoxon signed-rank test is the non-parametric alternative "
                    "to the paired t-test. It tests whether the median of within-pair "
                    "differences differs from zero. Unlike the sign test, it uses "
                    "the magnitude of differences as well as their direction, giving "
                    "greater power."
                ),
            },
            {
                "heading": "Assumptions",
                "type": "numbered_list",
                "items": [
                    ("Paired observations", "Each observation has a natural partner."),
                    ("Symmetry", "The distribution of differences is symmetric about the median (needed for exact inference)."),
                    ("Ordinal differences", "Differences can be meaningfully ranked."),
                ],
            },
            {
                "heading": "Procedure",
                "type": "numbered_list",
                "items": [
                    ("Compute differences", "D_i = X_1i − X_2i. Discard pairs where D_i = 0."),
                    ("Rank by magnitude", "Rank |D_i| from 1 (smallest) to n (largest). Average ranks for ties."),
                    ("Signed rank sums", "W+ = sum of ranks where D_i > 0. W− = sum of ranks where D_i < 0."),
                    ("Test statistic", "T = min(W+, W−). Refer to Wilcoxon tables or normal approximation for large n."),
                ],
            },
            {
                "heading": "W+ statistic",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$W^+ = \sum_{i: D_i > 0} R_i$",
                        "Sum of positive signed ranks. Under H₀ (median difference = 0), W+ ~ Wilcoxon distribution with n pairs.",
                    ),
                ],
                "source": "Wilcoxon (1945)",
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "scipy.stats.wilcoxon(x, y) computes the signed-rank test on "
                    "the paired differences x−y. Use alternative='two-sided', "
                    "'greater', or 'less'. "
                    "GraphPad Prism: 'Wilcoxon matched-pairs signed-rank test'."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Wilcoxon, F. (1945). Individual comparisons by ranking methods. Biometrics Bulletin, 1(6), 80-83.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 9: Kruskal-Wallis H
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Kruskal-Wallis H Test",
        "tags": ["scipy.stats.kruskal", "Non-parametric", "3+ groups"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "The Kruskal-Wallis H test is the non-parametric analogue of "
                    "one-way ANOVA. It tests whether k ≥ 2 independent groups come "
                    "from the same distribution by comparing mean ranks. "
                    "It does not require normality but assumes similar distribution "
                    "shapes if used to compare medians."
                ),
            },
            {
                "heading": "Assumptions",
                "type": "numbered_list",
                "items": [
                    ("Independence", "All observations are independent."),
                    ("Ordinal scale", "The outcome can be meaningfully ranked."),
                    ("Shape similarity", "If testing for median differences (not just stochastic dominance), groups should have similar distributional shapes."),
                ],
            },
            {
                "heading": "H statistic",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$H = \frac{12}{N(N+1)}\sum_{j=1}^k \frac{R_j^2}{n_j} - 3(N+1)$",
                        "H statistic, where N = total observations, n_j = group j size, R_j = sum of ranks in group j. Under H₀, H ~ χ²(k−1) for large samples.",
                    ),
                ],
                "source": "Kruskal & Wallis (1952)",
            },
            {
                "heading": "Tie correction",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$H_{corrected} = \frac{H}{1 - \frac{\sum_t (t^3 - t)}{N^3 - N}}$",
                        "Correction for ties: t is the number of tied observations in each tied group. Applied automatically by scipy.",
                    ),
                ],
            },
            {
                "heading": "Effect size",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\eta^2_H = \frac{H - k + 1}{N - k}$",
                        "Eta-squared from H: non-parametric effect size analogous to ANOVA η². Small ≈ 0.01, medium ≈ 0.06, large ≈ 0.14.",
                    ),
                ],
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "scipy.stats.kruskal(*groups) returns (H, p). "
                    "Follow significant results with Dunn's post-hoc test "
                    "or pairwise Mann-Whitney U tests with multiple comparison correction. "
                    "GraphPad Prism: 'Kruskal-Wallis test'."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Kruskal, W.H. & Wallis, W.A. (1952). Use of ranks in one-criterion variance analysis. JASA, 47(260), 583-621.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 10: Friedman Test
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Friedman Test",
        "tags": ["scipy.stats.friedmanchisquare", "Non-parametric", "Paired", "3+ groups"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "The Friedman test is the non-parametric analogue of one-way "
                    "repeated measures ANOVA. It ranks observations within each "
                    "block (subject) and tests whether the column rank sums differ. "
                    "Use when the normality or sphericity assumptions of repeated "
                    "measures ANOVA cannot be met."
                ),
            },
            {
                "heading": "Assumptions",
                "type": "numbered_list",
                "items": [
                    ("Blocked data", "Data are organised into b blocks (subjects), each observed under k conditions."),
                    ("Independence of blocks", "Blocks (subjects) are independent."),
                    ("Ordinal scale", "Observations can be meaningfully ranked within each block."),
                ],
            },
            {
                "heading": "χ²_F statistic",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\chi^2_F = \frac{12}{bk(k+1)}\sum_{j=1}^k R_j^2 - 3b(k+1)$",
                        "Friedman statistic, where b = number of blocks (subjects), k = conditions, R_j = sum of ranks in condition j. Under H₀, χ²_F ~ χ²(k−1) for large b.",
                    ),
                ],
                "source": "Friedman (1937)",
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "scipy.stats.friedmanchisquare(*conditions) returns (χ²_F, p). "
                    "Each argument is a list of values for one condition, "
                    "ordered by subject. "
                    "Post-hoc: Wilcoxon signed-rank tests on pairwise conditions "
                    "with Bonferroni or Holm correction."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Friedman, M. (1937). The use of ranks to avoid the assumption of normality implicit in the analysis of variance. JASA, 32(200), 675-701.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 11: Log-rank (Mantel-Cox) Test
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Log-rank (Mantel-Cox) Test",
        "tags": ["Survival"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "The log-rank test compares survival curves between two or more "
                    "groups. It is the most commonly used test in survival analysis "
                    "and is most powerful when the hazard ratio is approximately "
                    "constant over time (proportional hazards assumption). "
                    "It makes no assumption about the shape of the survival distribution."
                ),
            },
            {
                "heading": "Kaplan-Meier estimator",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\hat{S}(t) = \prod_{t_i \leq t} \left(1 - \frac{d_i}{n_i}\right)$",
                        "Product-limit estimator of the survival function. At each event time t_i: d_i = number of events, n_i = number at risk. Handles censored observations.",
                    ),
                ],
                "source": "Kaplan & Meier (1958)",
            },
            {
                "heading": "Greenwood's variance formula",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\widehat{\mathrm{Var}}[\hat{S}(t)] = [\hat{S}(t)]^2 \sum_{t_i \leq t} \frac{d_i}{n_i(n_i - d_i)}$",
                        "Greenwood's formula for the variance of the KM estimate. Used to construct pointwise confidence intervals for the survival curve.",
                    ),
                ],
            },
            {
                "heading": "Log-rank statistic",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\chi^2_{LR} = \frac{\left(\sum_j (O_{1j} - E_{1j})\right)^2}{\sum_j V_j}$",
                        "Log-rank χ² statistic, summed over all event times j. O = observed events, E = expected under equal hazard assumption, V = variance. Under H₀, χ²_LR ~ χ²(1) for 2 groups.",
                    ),
                ],
                "source": "Mantel (1966)",
            },
            {
                "heading": "When to use",
                "type": "text",
                "body": (
                    "Use log-rank when survival curves are expected to separate early "
                    "and stay separated (proportional hazards). "
                    "When curves cross or hazard ratio changes over time, consider "
                    "the Breslow/Wilcoxon test (weights early events more heavily) or "
                    "restricted mean survival time analysis."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Kaplan, E.L. & Meier, P. (1958). Nonparametric estimation from incomplete observations. JASA, 53(282), 457-481.",
                    "Mantel, N. (1966). Evaluation of survival data and two new rank order statistics arising in its consideration. Cancer Chemotherapy Reports, 50(3), 163-170.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 12: Fisher's Exact Test
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Fisher's Exact Test",
        "tags": ["scipy.stats.fisher_exact", "Categorical", "2x2"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "Fisher's exact test evaluates independence in a 2×2 contingency "
                    "table without relying on the chi-square approximation. "
                    "It computes the exact probability of observing a table as "
                    "extreme as (or more extreme than) the one obtained, given the "
                    "fixed marginal totals. Use instead of chi-square when expected "
                    "cell counts are small (any expected count < 5, or total n < 20)."
                ),
            },
            {
                "heading": "Hypergeometric probability",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$P = \frac{\binom{R_1}{a}\binom{R_2}{c}}{\binom{N}{n_1}}$",
                        "Probability of a specific 2×2 table given fixed marginals. "
                        "R₁, R₂ = row totals; n₁ = column 1 total; a, c = cell counts; N = grand total. "
                        "p-value = sum over all tables at least as extreme.",
                    ),
                ],
                "source": "Agresti (2002)",
            },
            {
                "heading": "When to use Fisher's vs chi-square",
                "type": "numbered_list",
                "items": [
                    ("Small samples", "Use Fisher's when any expected cell count < 5, or when n < 20."),
                    ("Large samples", "Chi-square is adequate when all expected counts ≥ 5. Computationally simpler."),
                    ("Exact p-values", "Fisher's gives exact p-values; chi-square is asymptotic."),
                    ("2×2 only", "Fisher's exact test is defined for 2×2 tables. For larger tables, use chi-square or Freeman-Halton extension."),
                ],
            },
            {
                "heading": "Odds ratio",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$OR = \frac{a \cdot d}{b \cdot c}$",
                        "Odds ratio for a 2×2 table with cells a, b, c, d (row 1: a,b; row 2: c,d). OR > 1 indicates higher odds in row 1.",
                    ),
                ],
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "scipy.stats.fisher_exact([[a,b],[c,d]], alternative='two-sided') "
                    "returns (odds_ratio, p_value). "
                    "GraphPad Prism: 'Fisher's exact test' in the Contingency section."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Agresti, A. (2002). Categorical Data Analysis, 2nd ed. New York: Wiley.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 13: Chi-square Test of Independence
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Chi-square Test of Independence",
        "tags": ["scipy.stats.chi2_contingency", "Categorical"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "The chi-square test of independence tests whether two categorical "
                    "variables are associated in an r×c contingency table. "
                    "It compares observed cell frequencies to those expected if the "
                    "variables were independent."
                ),
            },
            {
                "heading": "Assumptions",
                "type": "numbered_list",
                "items": [
                    ("Independence", "Observations are independent."),
                    ("Expected counts", "All expected cell counts should be ≥ 5 (use Fisher's exact for 2×2 with small counts)."),
                    ("Categorical variables", "Both variables must be categorical (nominal or ordinal)."),
                ],
            },
            {
                "heading": "Chi-square statistic",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$E_{ij} = \frac{R_i \cdot C_j}{N}$",
                        "Expected count for cell (i,j): row total R_i × column total C_j, divided by grand total N.",
                    ),
                    (
                        r"$\chi^2 = \sum_{i,j} \frac{(O_{ij} - E_{ij})^2}{E_{ij}}$",
                        "Chi-square statistic: sum over all cells. Under H₀ (independence), χ² ~ χ²((r−1)(c−1)).",
                    ),
                ],
                "source": "Casella & Berger §8.3; Agresti (2002)",
            },
            {
                "heading": "Effect size: Cramér's V",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$V = \sqrt{\frac{\chi^2}{N \cdot \min(r-1, c-1)}}$",
                        "Cramér's V: ranges from 0 (no association) to 1 (perfect association). Interpretable for tables of any size.",
                    ),
                ],
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "scipy.stats.chi2_contingency(table) returns (χ², p, df, expected). "
                    "With correction=True (default for 2×2), Yates' continuity correction is applied. "
                    "GraphPad Prism: 'Chi-square test' in the Contingency section."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Casella, G. & Berger, R.L. (2002). Statistical Inference, 2nd ed. §8.3.",
                    "Agresti, A. (2002). Categorical Data Analysis, 2nd ed. New York: Wiley.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 14: Chi-square Goodness of Fit
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Chi-square Goodness of Fit",
        "tags": ["scipy.stats.chisquare", "Categorical"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "The chi-square goodness-of-fit test determines whether observed "
                    "frequencies in a single categorical variable match expected "
                    "frequencies from a hypothesised distribution. "
                    "Unlike the test of independence, it operates on a single "
                    "1-D frequency distribution."
                ),
            },
            {
                "heading": "Test statistic",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\chi^2 = \sum_{i=1}^k \frac{(O_i - E_i)^2}{E_i}$",
                        "Goodness-of-fit statistic. Under H₀ (observed frequencies match expected), χ² ~ χ²(df). df = k − 1 − p, where p = number of parameters estimated from data.",
                    ),
                ],
                "source": "Casella & Berger §8.3",
            },
            {
                "heading": "Degrees of freedom",
                "type": "text",
                "body": (
                    "df = k − 1 when expected frequencies are fully specified a priori "
                    "(no parameters estimated from data). "
                    "Subtract one additional df for each parameter estimated from the "
                    "observed data to specify the expected distribution "
                    "(e.g., df = k − 3 for a normal fit where mean and SD are estimated)."
                ),
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "scipy.stats.chisquare(f_obs, f_exp=None) returns (χ², p). "
                    "If f_exp is None, equal expected frequencies are assumed. "
                    "All expected counts should be ≥ 5."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Casella, G. & Berger, R.L. (2002). Statistical Inference, 2nd ed. §8.3.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 15: Pearson Correlation
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Pearson Correlation",
        "tags": ["scipy.stats.pearsonr", "Continuous"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "Pearson's r measures the strength and direction of the linear "
                    "relationship between two continuous variables. It ranges from "
                    "−1 (perfect negative linear relationship) to +1 (perfect positive). "
                    "It quantifies the degree to which two variables co-vary linearly, "
                    "standardised by their individual variabilities."
                ),
            },
            {
                "heading": "Assumptions",
                "type": "numbered_list",
                "items": [
                    ("Linearity", "The relationship between X and Y is linear."),
                    ("Bivariate normality", "For inferential tests (p-values), both variables should be approximately normally distributed."),
                    ("Interval scale", "Both variables are measured on interval or ratio scales."),
                    ("Absence of outliers", "Pearson r is sensitive to outliers."),
                ],
            },
            {
                "heading": "Formula",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$r = \frac{\sum_{i=1}^n (X_i - \bar{X})(Y_i - \bar{Y})}{\sqrt{\sum_{i=1}^n(X_i-\bar{X})^2 \cdot \sum_{i=1}^n(Y_i-\bar{Y})^2}}$",
                        "Pearson r: ratio of covariance to product of standard deviations. Equivalent to: r = cov(X,Y) / (s_X · s_Y).",
                    ),
                ],
                "source": "Casella & Berger §7.2",
            },
            {
                "heading": "Significance test",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$t = \frac{r\sqrt{n-2}}{\sqrt{1-r^2}}$",
                        "Under H₀: ρ = 0, this t statistic follows t(n−2).",
                    ),
                ],
                "source": "Casella & Berger §7.2",
            },
            {
                "heading": "Fisher z-transform (for CI and comparing correlations)",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$z = \frac{1}{2}\ln\!\left(\frac{1+r}{1-r}\right) = \tanh^{-1}(r)$",
                        "Fisher's z-transform stabilises the variance. Under H₀, z is approximately normal with SE = 1/√(n−3). Use to construct CIs for ρ or to compare two independent correlations.",
                    ),
                ],
                "source": "Fisher (1921)",
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "scipy.stats.pearsonr(x, y) returns (r, p). "
                    "For confidence intervals, apply Fisher z-transform, compute "
                    "z ± 1.96/√(n−3), then back-transform using tanh()."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Casella, G. & Berger, R.L. (2002). Statistical Inference, 2nd ed. §7.2.",
                    "Fisher, R.A. (1921). On the probable error of a coefficient of correlation deduced from a small sample. Metron, 1, 3-32.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 16: Spearman Rank Correlation
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Spearman Rank Correlation",
        "tags": ["scipy.stats.spearmanr", "Non-parametric"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "Spearman's ρ (rho) is the non-parametric analogue of Pearson r. "
                    "It measures the strength of the monotonic (not necessarily linear) "
                    "relationship between two variables. It is computed as the Pearson "
                    "correlation of the rank-transformed variables, making it robust "
                    "to outliers and appropriate for ordinal data."
                ),
            },
            {
                "heading": "Primary definition (ranks)",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\rho_s = r_{\mathrm{rank}(X),\,\mathrm{rank}(Y)}$",
                        "Spearman's ρ is the Pearson correlation of the ranked variables. This is the general definition that handles ties correctly.",
                    ),
                ],
                "source": "Spearman (1904)",
            },
            {
                "heading": "Shortcut formula (no ties only)",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\rho_s = 1 - \frac{6\sum_{i=1}^n d_i^2}{n(n^2-1)}$",
                        "Shortcut: d_i = rank(X_i) − rank(Y_i). Valid ONLY when there are no ties. With ties, use the Pearson-on-ranks formula.",
                    ),
                ],
            },
            {
                "heading": "Significance test",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$t = \frac{\rho_s\sqrt{n-2}}{\sqrt{1-\rho_s^2}}$",
                        "Approximate t-test for H₀: ρ = 0, with df = n−2. Accurate for n ≥ 10.",
                    ),
                ],
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "scipy.stats.spearmanr(x, y) returns (ρ, p). "
                    "Handles ties via the rank formulation. "
                    "GraphPad Prism: 'Spearman correlation'."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Spearman, C. (1904). The proof and measurement of association between two things. American Journal of Psychology, 15(1), 72-101.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 17: Permutation Test
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Permutation Test",
        "tags": ["Distribution-free"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "Permutation (randomisation) tests generate a null distribution "
                    "empirically by repeatedly shuffling group labels and recomputing "
                    "the test statistic. The p-value is the proportion of permutations "
                    "that produce a statistic at least as extreme as the observed value. "
                    "No distributional assumptions are required."
                ),
            },
            {
                "heading": "Algorithm",
                "type": "numbered_list",
                "items": [
                    ("Compute observed statistic", "Calculate the test statistic T_obs from the original data (e.g., difference of means, F ratio)."),
                    ("Permute labels", "Randomly reassign group labels (keeping group sizes fixed) and recompute T."),
                    ("Repeat", "Repeat B times (typically B ≥ 10,000) to build the null distribution of T."),
                    ("P-value", "p = (number of permutations with |T| ≥ |T_obs|) / B. Exact when all permutations are enumerated."),
                ],
            },
            {
                "heading": "Permutation p-value",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$p = \frac{1 + \#\{T^* \geq T_{obs}\}}{B + 1}$",
                        "The +1 in numerator and denominator (Phipson & Smyth 2010) avoids p = 0 and preserves Type I error control. T* are permutation statistics, B is the number of permutations.",
                    ),
                ],
            },
            {
                "heading": "When to use",
                "type": "text",
                "body": (
                    "Permutation tests are particularly valuable when:\n"
                    "• Sample sizes are too small for asymptotic tests to be reliable.\n"
                    "• The data distribution is clearly non-normal and non-parametric "
                    "rank tests are not appropriate (e.g., complex multivariate statistics).\n"
                    "• You want an exact test without distributional assumptions.\n\n"
                    "Claude Plotter uses permutation tests as an alternative to "
                    "parametric tests in the statistics panel."
                ),
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 18: Bland-Altman Analysis
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Bland-Altman Analysis",
        "tags": ["Agreement"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "Bland-Altman analysis assesses the agreement between two "
                    "measurement methods — it is NOT a statistical test for a difference. "
                    "A correlation coefficient or t-test cannot determine whether two "
                    "methods agree; Bland-Altman plots visualise the distribution of "
                    "differences as a function of the average measurement."
                ),
            },
            {
                "heading": "Construction",
                "type": "numbered_list",
                "items": [
                    ("Compute differences", "D_i = Method A_i − Method B_i for each subject."),
                    ("Compute averages", "M_i = (Method A_i + Method B_i) / 2 for each subject."),
                    ("Plot", "Scatter plot of D_i (y-axis) vs M_i (x-axis)."),
                    ("Add reference lines", "Mean difference (bias) and limits of agreement."),
                ],
            },
            {
                "heading": "Limits of agreement",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\bar{D} \pm 1.96 \cdot s_D$",
                        "95% limits of agreement (LoA): the range within which ~95% of differences between methods are expected to fall. Clinical judgement determines whether this range is acceptably narrow.",
                    ),
                ],
            },
            {
                "heading": "CI for the mean difference",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\bar{D} \pm t_{n-1,\,0.025} \cdot \frac{s_D}{\sqrt{n}}$",
                        "95% CI for the mean bias. Tells you whether the systematic difference is statistically different from zero.",
                    ),
                ],
            },
            {
                "heading": "Interpretation",
                "type": "text",
                "body": (
                    "A mean difference near zero indicates no systematic bias. "
                    "Wide limits of agreement indicate poor method agreement even if "
                    "the mean difference is small. "
                    "Funnel-shaped patterns (differences increasing with average) "
                    "suggest proportional bias — consider log-transforming data."
                ),
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 19: Tukey HSD
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Tukey HSD Post-hoc Test",
        "tags": ["Post-hoc", "Parametric"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "Tukey's Honestly Significant Difference (HSD) test performs all "
                    "pairwise comparisons after ANOVA while controlling the family-wise "
                    "error rate (FWER) at α. It uses the studentized range distribution "
                    "and is exact for balanced designs (equal group sizes)."
                ),
            },
            {
                "heading": "HSD formula",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$HSD = q_{\alpha, k, N-k} \cdot \sqrt{\frac{MS_{within}}{n}}$",
                        "Minimum difference between means to be declared significant. q is the critical value from the studentized range distribution with k groups and N−k error df.",
                    ),
                ],
                "source": "Tukey (1949)",
            },
            {
                "heading": "Confidence intervals",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$(\bar{X}_j - \bar{X}_i) \pm q_{\alpha,k,N-k} \cdot \sqrt{\frac{MS_{within}}{n}}$",
                        "Simultaneous 100(1−α)% CIs for all pairwise differences. All intervals are valid simultaneously at the stated confidence level.",
                    ),
                ],
            },
            {
                "heading": "When to use Tukey",
                "type": "text",
                "body": (
                    "Use Tukey HSD when:\n"
                    "• All pairwise comparisons are of interest.\n"
                    "• Groups are roughly equal in size.\n"
                    "• You want simultaneous CIs.\n\n"
                    "Tukey is more powerful than Bonferroni for all-pairs comparisons. "
                    "For comparisons only against a control group, Dunnett is more powerful. "
                    "For unequal variances, use Games-Howell."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Tukey, J.W. (1949). Comparing individual means in the analysis of variance. Biometrics, 5(2), 99-114.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 20: Bonferroni Correction
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Bonferroni Correction",
        "tags": ["Multiple comparisons"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "The Bonferroni correction controls the family-wise error rate "
                    "(FWER) when conducting m simultaneous hypothesis tests. "
                    "It is the simplest and most conservative method, requiring no "
                    "assumptions about the dependence structure between tests."
                ),
            },
            {
                "heading": "Corrected significance threshold",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\alpha^* = \frac{\alpha}{m}$",
                        "Reject H_i if p_i ≤ α/m. This guarantees FWER ≤ α regardless of dependence among tests.",
                    ),
                ],
                "source": "Dunn (1961)",
            },
            {
                "heading": "Equivalently: adjusted p-values",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$p_i^{adj} = \min(m \cdot p_i,\; 1)$",
                        "Bonferroni-adjusted p-value: compare against the original α. Capped at 1.",
                    ),
                ],
            },
            {
                "heading": "Limitation",
                "type": "text",
                "body": (
                    "Bonferroni is exact only when tests are independent. "
                    "For positively correlated tests (common in practice), it is "
                    "conservative — the actual FWER is below α. "
                    "Holm-Bonferroni is uniformly more powerful and is preferred "
                    "whenever Bonferroni correction is appropriate."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Dunn, O.J. (1961). Multiple comparisons among means. JASA, 56(293), 52-64.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 21: Holm-Bonferroni
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Holm-Bonferroni (Step-down) Correction",
        "tags": ["Multiple comparisons"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "The Holm-Bonferroni procedure is a step-down modification of "
                    "the Bonferroni correction. It is uniformly more powerful than "
                    "Bonferroni (never less powerful) while still controlling the FWER "
                    "at α. It is the recommended replacement for Bonferroni in most settings."
                ),
            },
            {
                "heading": "Procedure",
                "type": "numbered_list",
                "items": [
                    ("Rank p-values", "Order p-values from smallest to largest: p_(1) ≤ p_(2) ≤ … ≤ p_(m)."),
                    ("Compare sequentially", "For i = 1, 2, …, m: compare p_(i) to α/(m−i+1)."),
                    ("First non-rejection", "Reject H_(i) if p_(i) ≤ α/(m−i+1). Stop at the first i where p_(i) > α/(m−i+1) and retain all remaining H_(j)."),
                ],
            },
            {
                "heading": "Threshold at step i",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\alpha_i = \frac{\alpha}{m - i + 1}$",
                        "Critical threshold for the i-th ordered p-value. Thresholds increase from α/m (Bonferroni) to α as hypotheses are rejected.",
                    ),
                ],
                "source": "Holm (1979)",
            },
            {
                "heading": "Why it is more powerful",
                "type": "text",
                "body": (
                    "After rejecting the smallest p-value with threshold α/m, "
                    "the remaining m−1 tests use threshold α/(m−1) — larger than Bonferroni's α/m. "
                    "This step-down logic means Holm rejects at least as many hypotheses as Bonferroni, "
                    "and usually more."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics, 6(2), 65-70.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 22: Benjamini-Hochberg (FDR)
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Benjamini-Hochberg FDR Correction",
        "tags": ["Multiple comparisons", "FDR"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "The Benjamini-Hochberg (BH) procedure controls the False Discovery "
                    "Rate (FDR) — the expected proportion of rejected hypotheses that are "
                    "false positives — rather than the FWER. "
                    "FDR control is less stringent than FWER control, allowing more "
                    "rejections (higher power) at the cost of tolerating some false positives."
                ),
            },
            {
                "heading": "Procedure",
                "type": "numbered_list",
                "items": [
                    ("Rank p-values", "Order p-values from smallest to largest: p_(1) ≤ p_(2) ≤ … ≤ p_(m)."),
                    ("Find largest k", "Find the largest k such that p_(k) ≤ k·α/m."),
                    ("Reject", "Reject all H_(1), H_(2), …, H_(k)."),
                ],
            },
            {
                "heading": "BH threshold",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$p_{(k)} \leq \frac{k \cdot \alpha}{m}$",
                        "BH threshold for rank k. Reject all tests up to and including the largest k satisfying this. FDR is controlled at α when tests are independent (or positively correlated).",
                    ),
                ],
                "source": "Benjamini & Hochberg (1995)",
            },
            {
                "heading": "FWER vs FDR",
                "type": "text",
                "body": (
                    "FWER: P(at least one false positive) ≤ α. "
                    "Appropriate for confirmatory experiments where any false positive is costly.\n\n"
                    "FDR: E(false positives / total rejections) ≤ α. "
                    "Appropriate for exploratory analyses (e.g., genomics, proteomics) where "
                    "follow-up experiments will filter false positives."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Benjamini, Y. & Hochberg, Y. (1995). Controlling the false discovery rate. JRSS-B, 57(1), 289-300.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 23: Dunnett (vs control)
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Dunnett's Test (vs Control)",
        "tags": ["Post-hoc", "Parametric"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "Dunnett's test compares each of k−1 treatment groups to a single "
                    "control group, controlling the FWER at α. "
                    "Because it performs only k−1 comparisons (not all k(k−1)/2 pairs), "
                    "it is more powerful than Tukey HSD for control-vs-treatment designs."
                ),
            },
            {
                "heading": "Test statistic for each treatment vs control",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$d_j = \frac{\bar{X}_j - \bar{X}_0}{\sqrt{MS_{within}\left(\frac{1}{n_j} + \frac{1}{n_0}\right)}}$",
                        "Dunnett's statistic for treatment j vs control (group 0). Compared to the Dunnett critical value, not the standard t critical value.",
                    ),
                ],
                "source": "Dunnett (1955)",
            },
            {
                "heading": "When to use",
                "type": "text",
                "body": (
                    "Use Dunnett's test when:\n"
                    "• One group is designated as control and all others are treatments.\n"
                    "• You are not interested in treatment-vs-treatment comparisons.\n"
                    "• You want maximum power for control comparisons.\n\n"
                    "GraphPad Prism: 'Dunnett's multiple comparisons test' after one-way ANOVA."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Dunnett, C.W. (1955). A multiple comparison procedure for comparing several treatments with a control. JASA, 50(272), 1096-1121.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 24: Dunn's Test
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Dunn's Test (Non-parametric Post-hoc)",
        "tags": ["Post-hoc", "Non-parametric"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "Dunn's test is the standard pairwise post-hoc procedure following "
                    "a significant Kruskal-Wallis test. It uses the overall rank "
                    "assignments from the Kruskal-Wallis test and applies a "
                    "multiple comparison correction (typically Bonferroni or Holm)."
                ),
            },
            {
                "heading": "Procedure",
                "type": "numbered_list",
                "items": [
                    ("Rank all observations", "Assign ranks 1 to N across all groups combined (using average ranks for ties)."),
                    ("Compute mean ranks", "Calculate the mean rank R̄_j for each group j."),
                    ("Pairwise z-test", "For each pair (j, j'): z = (R̄_j − R̄_j') / SE, where SE = sqrt[N(N+1)/12 · (1/n_j + 1/n_j') − tie_correction]."),
                    ("Apply correction", "Adjust p-values using Bonferroni, Holm, or Benjamini-Hochberg."),
                ],
            },
            {
                "heading": "Pairwise z statistic",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$z_{jj'} = \frac{\bar{R}_j - \bar{R}_{j'}}{\sqrt{\frac{N(N+1)}{12}\left(\frac{1}{n_j} + \frac{1}{n_{j'}}\right)}}$",
                        "Dunn's z for the comparison between groups j and j'. Compare to standard normal critical values after applying multiple comparison correction.",
                    ),
                ],
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "Python: scikit_posthocs.posthoc_dunn(data, p_adjust='holm') "
                    "or pingouin.pairwise_tests(parametric=False). "
                    "GraphPad Prism: 'Dunn's multiple comparisons test' after Kruskal-Wallis."
                ),
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 25: Shapiro-Wilk
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Shapiro-Wilk Normality Test",
        "tags": ["scipy.stats.shapiro", "Normality"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "The Shapiro-Wilk test is the most powerful test for normality "
                    "for small to moderate sample sizes (n ≤ 2000). "
                    "It tests H₀: the sample comes from a normal distribution. "
                    "A significant result (small W, small p) indicates departure from normality."
                ),
            },
            {
                "heading": "W statistic",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$W = \frac{\left(\sum_{i=1}^n a_i X_{(i)}\right)^2}{\sum_{i=1}^n (X_i - \bar{X})^2}$",
                        "W ranges from 0 to 1. Values near 1 indicate normality. The coefficients a_i are derived from the expected order statistics of a normal distribution.",
                    ),
                ],
                "source": "Shapiro & Wilk (1965)",
            },
            {
                "heading": "Interpretation guidelines",
                "type": "text",
                "body": (
                    "• p > 0.05: fail to reject normality — proceed with parametric tests.\n"
                    "• p ≤ 0.05: evidence of non-normality — consider non-parametric tests.\n\n"
                    "Important caveats:\n"
                    "• Very small samples: low power — normality cannot be ruled out.\n"
                    "• Very large samples: high power — trivial departures become significant.\n"
                    "• Always examine Q-Q plots alongside the p-value.\n"
                    "• Parametric tests are often robust to mild non-normality, "
                    "especially with n ≥ 30 (Central Limit Theorem)."
                ),
            },
            {
                "heading": "Implementation note",
                "type": "text",
                "body": (
                    "scipy.stats.shapiro(data) returns (W, p). "
                    "For n > 5000, scipy uses an approximation. "
                    "For large n, the D'Agostino-Pearson K² test (scipy.stats.normaltest) "
                    "is preferred."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Shapiro, S.S. & Wilk, M.B. (1965). An analysis of variance test for normality. Biometrika, 52(3-4), 591-611.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 26: Levene's Test (Brown-Forsythe variant)
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Levene's Test (Equality of Variances)",
        "tags": ["scipy.stats.levene", "Variance"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "Levene's test evaluates H₀: all groups have equal population variances "
                    "(homoscedasticity). It is a prerequisite check for tests that assume "
                    "equal variances (e.g., Student's t, one-way ANOVA).\n\n"
                    "IMPORTANT: scipy.stats.levene() implements the Brown-Forsythe (1974) "
                    "variant by default (center='median'), which is more robust to "
                    "non-normality than the original Levene (1960) mean-centred version."
                ),
            },
            {
                "heading": "Brown-Forsythe variant",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$Z_{ij} = |X_{ij} - \tilde{X}_j|$",
                        "Absolute deviation from the group median X̃_j. This median centering makes the test robust to skewed distributions.",
                    ),
                    (
                        r"$F = \frac{(N-k)\sum_{j=1}^k n_j (\bar{Z}_j - \bar{Z})^2}{(k-1)\sum_{j=1}^k \sum_{i=1}^{n_j}(Z_{ij} - \bar{Z}_j)^2}$",
                        "F statistic applied to the Z_ij values. Under H₀, F ~ F(k−1, N−k).",
                    ),
                ],
                "source": "Brown & Forsythe (1974)",
            },
            {
                "heading": "Original Levene (mean-centred)",
                "type": "text",
                "body": (
                    "The original Levene (1960) test uses Z_ij = |X_ij − X̄_j| "
                    "(deviation from group mean). This is less robust when data are "
                    "non-normal. scipy.stats.levene(center='mean') reproduces this version."
                ),
            },
            {
                "heading": "Interpretation",
                "type": "text",
                "body": (
                    "• p > 0.05: fail to reject equal variances — Student's t / ANOVA assumptions met.\n"
                    "• p ≤ 0.05: variances differ — use Welch's t-test or Welch ANOVA instead.\n\n"
                    "Like all null-hypothesis tests, Levene's is sensitive to n: "
                    "small samples may miss real heteroscedasticity; "
                    "large samples may flag trivial differences."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Brown, M.B. & Forsythe, A.B. (1974). Robust tests for the equality of variances. JASA, 69(346), 364-367.",
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 27: Effect Size Reference
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Effect Size Reference",
        "tags": ["Effect size"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "Effect sizes quantify the magnitude of a result independently of "
                    "sample size. A statistically significant result can have a trivial "
                    "effect size; a non-significant result may reflect inadequate power "
                    "rather than a small effect. Always report effect sizes alongside p-values.\n\n"
                    "Note: Cohen's (1988) benchmarks (small/medium/large) are guidelines "
                    "for social science and should be interpreted in the context of "
                    "each specific research domain."
                ),
            },
            {
                "heading": "Cohen's d (two independent groups)",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$d = \frac{\bar{X}_1 - \bar{X}_2}{s_p}$",
                        "Standardised mean difference. Small: |d| ≈ 0.2, Medium: |d| ≈ 0.5, Large: |d| ≈ 0.8 (Cohen 1988 — discipline-specific).",
                    ),
                ],
                "source": "Cohen (1988)",
            },
            {
                "heading": "Hedges' g (bias-corrected d)",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$g = d \cdot \left(1 - \frac{3}{4(n_1 + n_2 - 2) - 1}\right)$",
                        "Bias-corrected effect size. Preferred over d for small samples (n < 20 per group). Same benchmarks as Cohen's d.",
                    ),
                ],
                "source": "Hedges (1981)",
            },
            {
                "heading": "Eta-squared (η²) — ANOVA",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\eta^2 = \frac{SS_{between}}{SS_{total}}$",
                        "Proportion of total variance explained by group. Biased upward in small samples. Small: 0.01, Medium: 0.06, Large: 0.14.",
                    ),
                ],
            },
            {
                "heading": "Partial eta-squared (η²_p) — factorial ANOVA",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\eta_p^2 = \frac{SS_{effect}}{SS_{effect} + SS_{error}}$",
                        "Effect SS as proportion of effect + error SS. Does not sum to 1 across effects. Common in factorial and repeated measures designs.",
                    ),
                ],
            },
            {
                "heading": "Omega-squared (ω²) — bias-corrected ANOVA",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$\omega^2 = \frac{SS_{between} - (k-1)MS_{within}}{SS_{total} + MS_{within}}$",
                        "Less biased than η². Preferred for reporting. Small: 0.01, Medium: 0.06, Large: 0.14.",
                    ),
                ],
                "source": "Cohen (1988)",
            },
            {
                "heading": "Cramér's V — chi-square",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$V = \sqrt{\frac{\chi^2}{N \cdot \min(r-1, c-1)}}$",
                        "Effect size for chi-square tests. Ranges 0–1. For 2×2 tables: Small ≈ 0.1, Medium ≈ 0.3, Large ≈ 0.5.",
                    ),
                ],
            },
            {
                "heading": "Rank-biserial correlation r_rb — Mann-Whitney",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$r_{rb} = \frac{U_1 - U_2}{n_1 \cdot n_2}$",
                        "Non-parametric effect size for Mann-Whitney U. Ranges −1 to +1. Interpretation: |r| ≈ 0.1 small, 0.3 medium, 0.5 large.",
                    ),
                ],
            },
            {
                "heading": "Common Language Effect Size (CL)",
                "type": "latex_block",
                "expressions": [
                    (
                        r"$CL = \Phi\!\left(\frac{d}{\sqrt{2}}\right)$",
                        "Probability that a randomly selected observation from group 1 exceeds one from group 2. Φ is the standard normal CDF. More intuitive than d for non-statisticians.",
                    ),
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 28: Choosing Parametric vs Non-parametric
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Choosing: Parametric vs Non-parametric Tests",
        "tags": ["Decision guide"],
        "subsections": [
            {
                "heading": "Overview",
                "type": "text",
                "body": (
                    "Parametric tests (t-test, ANOVA) assume the data follow a specific "
                    "distribution (usually normal). Non-parametric tests make fewer "
                    "assumptions but are generally less powerful when parametric "
                    "assumptions are met. The decision should be guided by sample size, "
                    "data characteristics, and robustness considerations."
                ),
            },
            {
                "heading": "Decision flowchart",
                "type": "numbered_list",
                "items": [
                    (
                        "Is the outcome ordinal only?",
                        "YES → use non-parametric tests (ranks are the natural scale). "
                        "NO → continue.",
                    ),
                    (
                        "Is n large (≥ 30 per group)?",
                        "YES → CLT makes parametric tests robust to non-normality for symmetric distributions. "
                        "Consider parametric. NO → continue.",
                    ),
                    (
                        "Are distributions approximately normal?",
                        "Check Shapiro-Wilk (W) and Q-Q plots. "
                        "YES → use parametric. NO/UNCERTAIN → continue.",
                    ),
                    (
                        "Are distributions symmetric?",
                        "YES → parametric tests remain approximately valid. "
                        "NO (skewed/bimodal) → non-parametric tests recommended.",
                    ),
                    (
                        "Are sample sizes equal across groups?",
                        "Equal n makes parametric ANOVA more robust to heteroscedasticity. "
                        "Unequal n with unequal variances → Welch ANOVA.",
                    ),
                ],
            },
            {
                "heading": "Parametric vs non-parametric comparison table",
                "type": "numbered_list",
                "items": [
                    ("Independent 2 groups", "Welch t-test ↔ Mann-Whitney U"),
                    ("Paired 2 groups", "Paired t-test ↔ Wilcoxon signed-rank"),
                    ("Independent 3+ groups", "One-way ANOVA ↔ Kruskal-Wallis"),
                    ("Paired 3+ groups", "Repeated measures ANOVA ↔ Friedman"),
                    ("Correlation", "Pearson r ↔ Spearman ρ"),
                ],
            },
            {
                "heading": "Power considerations",
                "type": "text",
                "body": (
                    "When normality holds, parametric tests have ~95–99% of their "
                    "optimal power while non-parametric tests lose ~5–10% (asymptotic "
                    "relative efficiency of Mann-Whitney vs t ≈ 0.955 for normal data). "
                    "When data are non-normal, non-parametric tests can be more powerful "
                    "than parametric alternatives — sometimes dramatically so for heavy-tailed "
                    "or skewed distributions."
                ),
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────
    # SECTION 29: Multiple Comparisons — Why and How
    # ─────────────────────────────────────────────────────────────────
    {
        "title": "Multiple Comparisons — Why and How",
        "tags": ["Multiple comparisons", "Decision guide"],
        "subsections": [
            {
                "heading": "The multiple comparisons problem",
                "type": "text",
                "body": (
                    "When m independent tests are each conducted at α = 0.05, "
                    "the probability of at least one false positive is:\n\n"
                    "   P(at least one false positive) = 1 − (1 − 0.05)^m\n\n"
                    "For m = 10: 40%. For m = 20: 64%. For m = 100: 99.4%.\n\n"
                    "Correction is needed to maintain the overall (family-wise) "
                    "error rate at α."
                ),
            },
            {
                "heading": "FWER vs FDR — choose based on context",
                "type": "numbered_list",
                "items": [
                    (
                        "FWER control",
                        "Controls P(any false positive) ≤ α. "
                        "Use for confirmatory experiments, clinical trials, small number of planned comparisons. "
                        "Methods: Bonferroni, Holm (recommended), Tukey HSD, Dunnett.",
                    ),
                    (
                        "FDR control",
                        "Controls expected proportion of false positives among rejections. "
                        "Use for exploratory analyses with many tests (genomics, proteomics, imaging). "
                        "Methods: Benjamini-Hochberg (recommended), Benjamini-Yekutieli.",
                    ),
                ],
            },
            {
                "heading": "Recommendation hierarchy for Claude Plotter users",
                "type": "numbered_list",
                "items": [
                    (
                        "Post-hoc after ANOVA (all pairs)",
                        "Use Tukey HSD. More powerful than Bonferroni for all-pairs comparisons.",
                    ),
                    (
                        "Post-hoc after ANOVA (vs control only)",
                        "Use Dunnett's test. More powerful than Tukey for control comparisons.",
                    ),
                    (
                        "Post-hoc after Kruskal-Wallis",
                        "Use Dunn's test with Holm correction.",
                    ),
                    (
                        "General FWER control",
                        "Use Holm-Bonferroni. Always at least as powerful as Bonferroni.",
                    ),
                    (
                        "Exploratory / many tests",
                        "Use Benjamini-Hochberg FDR at α = 0.05 or 0.10.",
                    ),
                    (
                        "When to skip correction",
                        "Pre-specified primary endpoint with a single comparison requires no correction. "
                        "Correction is for families of related tests.",
                    ),
                ],
            },
            {
                "heading": "When NOT to correct",
                "type": "text",
                "body": (
                    "Multiple comparison correction is not always needed:\n"
                    "• A single pre-specified hypothesis test (no family of tests).\n"
                    "• Descriptive analyses where false positives have low cost.\n"
                    "• Mechanistically independent tests (each test addresses a "
                    "separate scientific question).\n\n"
                    "Over-correction (applying FWER control to FDR settings) "
                    "reduces power unnecessarily and may cause real findings to be missed."
                ),
            },
            {
                "heading": "References",
                "type": "references",
                "items": [
                    "Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics, 6(2), 65-70.",
                    "Benjamini, Y. & Hochberg, Y. (1995). Controlling the false discovery rate. JRSS-B, 57(1), 289-300.",
                    "Tukey, J.W. (1949). Comparing individual means in the analysis of variance. Biometrics, 5(2), 99-114.",
                    "Dunnett, C.W. (1955). A multiple comparison procedure for comparing several treatments with a control. JASA, 50(272), 1096-1121.",
                ],
            },
        ],
    },

]  # end WIKI_SECTIONS


# ═══════════════════════════════════════════════════════════════════
# MASTER REFERENCES
# ═══════════════════════════════════════════════════════════════════

MASTER_REFERENCES = {
    "casella_berger_2002": (
        "Casella, G. & Berger, R.L. (2002). Statistical Inference, 2nd ed. "
        "Pacific Grove, CA: Duxbury/Thomson Learning."
    ),
    "welch_1947": (
        "Welch, B.L. (1947). The generalization of Student's problem when several "
        "different population variances are involved. Biometrika, 34(1-2), 28-35."
    ),
    "satterthwaite_1946": (
        "Satterthwaite, F.E. (1946). An approximate distribution of estimates of "
        "variance components. Biometrics Bulletin, 2(6), 110-114."
    ),
    "cohen_1988": (
        "Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences, "
        "2nd ed. Hillsdale, NJ: Lawrence Erlbaum Associates."
    ),
    "hedges_1981": (
        "Hedges, L.V. (1981). Distribution theory for Glass's estimator of effect "
        "size. Journal of Educational Statistics, 6(2), 107-128."
    ),
    "mann_whitney_1947": (
        "Mann, H.B. & Whitney, D.R. (1947). On a test of whether one of two random "
        "variables is stochastically larger than the other. "
        "Annals of Mathematical Statistics, 18(1), 50-60."
    ),
    "wilcoxon_1945": (
        "Wilcoxon, F. (1945). Individual comparisons by ranking methods. "
        "Biometrics Bulletin, 1(6), 80-83."
    ),
    "kruskal_wallis_1952": (
        "Kruskal, W.H. & Wallis, W.A. (1952). Use of ranks in one-criterion "
        "variance analysis. JASA, 47(260), 583-621."
    ),
    "friedman_1937": (
        "Friedman, M. (1937). The use of ranks to avoid the assumption of normality "
        "implicit in the analysis of variance. JASA, 32(200), 675-701."
    ),
    "kaplan_meier_1958": (
        "Kaplan, E.L. & Meier, P. (1958). Nonparametric estimation from incomplete "
        "observations. JASA, 53(282), 457-481."
    ),
    "mantel_1966": (
        "Mantel, N. (1966). Evaluation of survival data and two new rank order "
        "statistics arising in its consideration. "
        "Cancer Chemotherapy Reports, 50(3), 163-170."
    ),
    "shapiro_wilk_1965": (
        "Shapiro, S.S. & Wilk, M.B. (1965). An analysis of variance test for "
        "normality. Biometrika, 52(3-4), 591-611."
    ),
    "brown_forsythe_1974": (
        "Brown, M.B. & Forsythe, A.B. (1974). Robust tests for the equality of "
        "variances. JASA, 69(346), 364-367."
    ),
    "tukey_1949": (
        "Tukey, J.W. (1949). Comparing individual means in the analysis of "
        "variance. Biometrics, 5(2), 99-114."
    ),
    "dunn_1961": (
        "Dunn, O.J. (1961). Multiple comparisons among means. JASA, 56(293), 52-64."
    ),
    "holm_1979": (
        "Holm, S. (1979). A simple sequentially rejective multiple test procedure. "
        "Scandinavian Journal of Statistics, 6(2), 65-70."
    ),
    "benjamini_hochberg_1995": (
        "Benjamini, Y. & Hochberg, Y. (1995). Controlling the false discovery rate. "
        "JRSS-B, 57(1), 289-300."
    ),
    "dunnett_1955": (
        "Dunnett, C.W. (1955). A multiple comparison procedure for comparing several "
        "treatments with a control. JASA, 50(272), 1096-1121."
    ),
    "agresti_2002": (
        "Agresti, A. (2002). Categorical Data Analysis, 2nd ed. New York: Wiley."
    ),
    "spearman_1904": (
        "Spearman, C. (1904). The proof and measurement of association between two "
        "things. American Journal of Psychology, 15(1), 72-101."
    ),
    "fisher_1921": (
        "Fisher, R.A. (1921). On the probable error of a coefficient of correlation "
        "deduced from a small sample. Metron, 1, 3-32."
    ),
}
