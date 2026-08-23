# Analysis summary: three sources, one entity (P4)

Task: match Prozorro contracts against the ЄДР register of legal entities
on the `identifier.id` field and name the ten suppliers paid the most.

The base is the counterparties of 500 contracts, 361 unique codes. The
register matched 245 and missed 116. The main reason is structural, not a
data defect: 111 of those 116 codes are ten digits long, which makes them
tax numbers of individuals and sole traders, absent from a register of
legal entities by design. Unexplained losses: 0.

The answer depends on those 116. The total across all suppliers is
100 889 609.46 UAH. Dropping the unmatched ones lowers it to
86 108 542.77 UAH, by 14.7%. The top ten changes either way: the sole
trader falls out and a dairy plant with 1 526 998.77 UAH takes the place.

Recommendation: publish both totals side by side and state the selection
rule. The 14.7% gap follows from a choice, and the choice belongs to
whoever ordered the report.
