# ruff: noqa: E501  (a table of fictional variables, one per line)
"""Write the fictional labelled set: ``variables.jsonl`` and ``expected.json``.

Fictional variables written for feature 004, each with the topics a person would choose from
the bundled CLOSER scheme. No study metadata. Writes to ``adhoc/tiered/`` (git-ignored):

    python specs/004-tiered-tagger/results/scripts/build_labelled_set.py
"""

import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[4] / "adhoc/tiered"

YN = [["1", "Yes"], ["2", "No"], ["-9", "Refused"], ["-8", "Don't know"]]
# (file, variable, label, values, expected topic ids)
ROWS = [
    # demographics
    ("s1", "cmage", "Age of cohort member at interview (years)", [], ["age"]),
    ("s1", "cmsex", "Sex of cohort member", [["1", "Male"], ["2", "Female"]], ["gender"]),
    (
        "s1",
        "ethnic6",
        "Ethnic group (6 categories)",
        [
            ["1", "White"],
            ["2", "Mixed"],
            ["3", "Indian"],
            ["4", "Pakistani/Bangladeshi"],
            ["5", "Black"],
            ["6", "Other"],
        ],
        ["ethnic_group"],
    ),
    (
        "s1",
        "cobirth",
        "Country of birth",
        [["1", "England"], ["2", "Wales"], ["3", "Scotland"], ["4", "Elsewhere"]],
        ["place_of_birth"],
    ),
    (
        "s1",
        "homelang",
        "Main language spoken at home",
        [["1", "English"], ["2", "Welsh"], ["3", "Other"]],
        ["languages"],
    ),
    (
        "s1",
        "relig",
        "Religion respondent belongs to",
        [["1", "None"], ["2", "Christian"], ["3", "Muslim"], ["4", "Other"]],
        ["religion"],
    ),
    # housing and environment
    (
        "s1",
        "tenure",
        "Housing tenure",
        [
            ["1", "Own outright"],
            ["2", "Mortgage"],
            ["3", "Rent from council"],
            ["4", "Rent privately"],
        ],
        ["housing"],
    ),
    (
        "s1",
        "nbsafe",
        "How safe do you feel walking alone in this area after dark",
        [["1", "Very safe"], ["4", "Very unsafe"]],
        ["neighbourhood"],
    ),
    (
        "s1",
        "commute",
        "Usual way of travelling to work",
        [["1", "Car"], ["2", "Bus"], ["3", "Walk"], ["4", "Cycle"]],
        ["travel_transport"],
    ),
    ("s1", "damp", "Is there damp or mould in the home", YN, ["housing", "environmental_exposure"]),
    ("s1", "moves5", "Number of house moves in the last five years", [], ["residential_mobility"]),
    # physical health
    (
        "s2",
        "genhlth",
        "Self-rated general health",
        [["1", "Excellent"], ["5", "Poor"]],
        ["general_health"],
    ),
    ("s2", "asthma", "Ever been told by a doctor you have asthma", YN, ["respiratory_system"]),
    ("s2", "bpsys", "Systolic blood pressure, first reading (mmHg)", [], ["cardiovascular_system"]),
    ("s2", "height", "Measured height (cm)", [], ["anthropometry"]),
    ("s2", "bmi", "Body mass index derived from measured height and weight", [], ["anthropometry"]),
    (
        "s2",
        "backpain",
        "Back pain lasting more than three months in the past year",
        YN,
        ["musculoskeletal_system"],
    ),
    ("s2", "diabetes", "Has diabetes (doctor diagnosed)", YN, ["endocrine_system"]),
    ("s2", "eyesight", "Wears glasses or contact lenses", YN, ["hearing_vision_speech"]),
    ("s2", "grip", "Maximum grip strength, dominant hand (kg)", [], ["physical_functioning"]),
    # mental health
    ("s2", "malaise", "Malaise inventory total score", [], ["mental_disorders"]),
    ("s2", "lifesat", "Satisfaction with life so far, 0 to 10", [], ["wellbeing"]),
    ("s2", "depdiag", "Ever diagnosed with depression", YN, ["mental_disorders"]),
    (
        "s2",
        "memtest",
        "Number of words recalled in delayed memory test",
        [],
        ["cognitive_function"],
    ),
    (
        "s2",
        "lonely",
        "How often do you feel lonely",
        [["1", "Never"], ["5", "Always"]],
        ["emotions", "social_support"],
    ),
    # health care
    ("s2", "gpvisit", "Number of visits to the GP in the last 12 months", [], ["health_services"]),
    (
        "s2",
        "hospnight",
        "Admitted to hospital overnight in the last year",
        YN,
        ["hospital_admissions"],
    ),
    ("s2", "mmrjab", "Child received MMR vaccination", YN, ["immunisations"]),
    ("s2", "statins", "Currently taking statins", YN, ["medications", "cardiovascular_system"]),
    ("s2", "privins", "Covered by private medical insurance", YN, ["health_insurance"]),
    # health behaviour
    ("s3", "smknow", "Currently smokes cigarettes", YN, ["smoking"]),
    ("s3", "units", "Units of alcohol drunk in the last week", [], ["alcohol"]),
    ("s3", "fruitveg", "Portions of fruit and vegetables eaten yesterday", [], ["diet_nutrition"]),
    (
        "s3",
        "exdays",
        "Days in the last week with 30 minutes of exercise",
        [],
        ["physical_activity"],
    ),
    ("s3", "sleephrs", "Hours of sleep on a typical school night", [], ["sleep"]),
    ("s3", "cannabis", "Ever tried cannabis", YN, ["substance_use"]),
    # family and social
    (
        "s3",
        "marstat",
        "Legal marital status",
        [["1", "Single"], ["2", "Married"], ["3", "Divorced"], ["4", "Widowed"]],
        ["marital_status"],
    ),
    ("s3", "hhsize", "Number of people in the household", [], ["household_composition"]),
    ("s3", "sibs", "Number of brothers and sisters", [], ["family_members"]),
    (
        "s3",
        "frndsee",
        "How often do you see friends",
        [["1", "Most days"], ["5", "Never"]],
        ["friends"],
    ),
    ("s3", "nursery", "Child attends a nursery or playgroup", YN, ["childcare", "pre_school"]),
    ("s3", "volunt", "Done any voluntary work in the last year", YN, ["social_capital"]),
    ("s3", "internet", "Has internet access at home", YN, ["technology"]),
    # education
    (
        "s3",
        "highqual",
        "Highest academic qualification",
        [["1", "None"], ["2", "GCSE"], ["3", "A level"], ["4", "Degree"]],
        ["qualifications"],
    ),
    (
        "s3",
        "uniapp",
        "Applied to university",
        YN,
        ["further_higher_education", "education_aspirations"],
    ),
    ("s3", "readtest", "Reading test score at age 10", [], ["cognitive_skills", "basic_skills"]),
    (
        "s3",
        "sen",
        "Child has a statement of special educational needs",
        YN,
        ["learning_difficulties"],
    ),
    ("s3", "truant", "Played truant from school in the last year", YN, ["school_engagement"]),
    ("s3", "jobtrain", "Received training from employer in the last year", YN, ["training"]),
    # employment and income
    (
        "s4",
        "econact",
        "Current economic activity",
        [["1", "Employed"], ["2", "Unemployed"], ["3", "Student"], ["4", "Retired"]],
        ["employment"],
    ),
    (
        "s4",
        "nssec",
        "NS-SEC class of current job",
        [["1", "Higher managerial"], ["8", "Never worked"]],
        ["social_class"],
    ),
    ("s4", "netpay", "Usual take-home pay per month (pounds)", [], ["income"]),
    ("s4", "savings", "Total amount of savings", [], ["assets", "finances"]),
    ("s4", "debtprob", "Has problems paying bills or debts", YN, ["finances"]),
    ("s4", "uc", "Receives Universal Credit", YN, ["benefits"]),
    ("s4", "pension", "Contributes to a workplace pension", YN, ["pensions"]),
    # attitudes
    ("s4", "votegen", "Voted in the last general election", YN, ["politics"]),
    (
        "s4",
        "trust",
        "Most people can be trusted",
        [["1", "Agree"], ["2", "Disagree"]],
        ["social_attitudes"],
    ),
    (
        "s4",
        "immig",
        "Immigration is good for the economy",
        [["1", "Agree"], ["5", "Disagree"]],
        ["social_attitudes"],
    ),
    # child development
    ("s4", "breastf", "Was the baby ever breastfed", YN, ["infant_feeding"]),
    (
        "s4",
        "walkage",
        "Age in months when child first walked unaided",
        [],
        ["developmental_milestones"],
    ),
    (
        "s4",
        "readbed",
        "How often parent reads to child at bedtime",
        [["1", "Every day"], ["5", "Never"]],
        ["parenting"],
    ),
    ("s4", "bpvs", "British Picture Vocabulary Scale score at age 3", [], ["language_vocabulary"]),
    # life events
    ("s5", "retired", "Has retired from paid work", YN, ["retirement"]),
    ("s5", "arrested", "Ever been arrested by the police", YN, ["crime_justice"]),
    ("s5", "bullied", "Bullied at school in the last year", YN, ["bullying"]),
    ("s5", "covidpos", "Ever tested positive for COVID-19", YN, ["covid19", "infections"]),
    # omics
    ("s5", "crp", "C-reactive protein from blood sample (mg/L)", [], ["biomarkers"]),
    ("s5", "dnacons", "Consent given for DNA extraction", YN, ["genetics"]),
    # pregnancy
    ("s5", "pregnow", "Currently pregnant", YN, ["pregnancy_history"]),
    ("s5", "birthwt", "Baby's birth weight (grams)", [], ["childbirth", "anthropometry"]),
    ("s5", "csect", "Baby delivered by caesarean section", YN, ["childbirth"]),
    # administration
    ("s5", "serial", "Household serial number", [], ["identifiers"]),
    ("s5", "wtcross", "Cross-sectional survey weight", [], ["survey_weights"]),
    (
        "s5",
        "intmode",
        "Mode of interview",
        [["1", "Face to face"], ["2", "Web"], ["3", "Phone"]],
        ["fieldwork"],
    ),
    # cross-area
    ("s6", "smkpreg", "Mother smoked during pregnancy", YN, ["smoking", "pregnancy_history"]),
    ("s6", "rentamt", "Amount of rent paid per month", [], ["housing", "consumption"]),
    ("s6", "drinkdrv", "Ever driven after drinking too much", YN, ["alcohol", "risk_taking"]),
    (
        "s6",
        "carerrole",
        "Provides unpaid care for a sick or disabled relative",
        YN,
        ["family_members", "social_support"],
    ),
    # fits nothing
    ("s6", "var097", "Q97", [], ["other"]),
    ("s6", "flagx", "Internal processing flag X", [["0", "Not set"], ["1", "Set"]], ["other"]),
    ("s6", "blank3", "Spare question slot 3", [], ["other"]),
]


def main() -> None:
    """Write the set, checking that no file/variable key repeats."""
    seen = set()
    with open(DATA / "variables.jsonl", "w") as out:
        for f, v, label, values, _ in ROWS:
            assert (f, v) not in seen, v
            seen.add((f, v))
            row = {"file": f, "variable": v, "label": label, "sweep": "1"}
            if values:
                row["values"] = values
            out.write(json.dumps(row) + "\n")
    with open(DATA / "expected.json", "w") as out:
        json.dump({f"{f}/{v}": e for f, v, _, _, e in ROWS}, out, indent=1)
    print(len(ROWS), "variables")


if __name__ == "__main__":
    main()
