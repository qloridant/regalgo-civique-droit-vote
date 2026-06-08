import pytest
from datetime import date, timedelta
from regalgo_civique_droit_vote import DroitVoteAlgorithm
from regalgo import AlgoInput, PersonInput


ELECTEUR_VALIDE = {
    "nationalite_francaise": True,
    "age": 25,
    "capacite_civique": True,
    "inscrit_listes_electorales": True,
}


def test_peut_voter():
    algo = DroitVoteAlgorithm()
    result = algo.compute(AlgoInput(data=ELECTEUR_VALIDE))
    assert result.value is True


def test_mineur_ne_peut_pas_voter():
    algo = DroitVoteAlgorithm()
    data = {**ELECTEUR_VALIDE, "age": 17}
    result = algo.compute(AlgoInput(data=data))
    assert result.value is False


def test_non_inscrit_ne_peut_pas_voter():
    algo = DroitVoteAlgorithm()
    data = {**ELECTEUR_VALIDE, "inscrit_listes_electorales": False}
    result = algo.compute(AlgoInput(data=data))
    assert result.value is False


def test_etranger_ne_peut_pas_voter():
    algo = DroitVoteAlgorithm()
    data = {**ELECTEUR_VALIDE, "nationalite_francaise": False}
    result = algo.compute(AlgoInput(data=data))
    assert result.value is False


def test_age_negatif_raises():
    algo = DroitVoteAlgorithm()
    with pytest.raises(ValueError, match="âge"):
        algo.compute(AlgoInput(data={**ELECTEUR_VALIDE, "age": -1}))


def test_algo_id_and_regulation():
    algo = DroitVoteAlgorithm()
    assert algo.algo_id == "civique.droit-vote.v1"
    assert algo.regulation["dct:title"] == "Code électoral"


# --- PersonInput (Core Vocabularies) ---

PERSON_VALIDE = PersonInput(
    cv_nationality="FR",
    schema_birth_date=date(1990, 6, 15),
    cccev_civil_rights_intact=True,
    cccev_electoral_list_registered=True,
)


def test_person_input_peut_voter():
    algo = DroitVoteAlgorithm()
    result = algo.compute(PERSON_VALIDE.to_algo_input())
    assert result.value is True


def test_person_input_nationalite_non_fr():
    algo = DroitVoteAlgorithm()
    person = PersonInput(
        cv_nationality="DE",
        schema_birth_date=date(1990, 6, 15),
        cccev_civil_rights_intact=True,
        cccev_electoral_list_registered=True,
    )
    result = algo.compute(person.to_algo_input())
    assert result.value is False


def test_person_input_mineur():
    algo = DroitVoteAlgorithm()
    today = date.today()
    # né il y a exactement 17 ans et 1 jour
    birth_date = today - timedelta(days=17 * 365 + 1)
    person = PersonInput(
        cv_nationality="FR",
        schema_birth_date=birth_date,
        cccev_civil_rights_intact=True,
        cccev_electoral_list_registered=True,
    )
    result = algo.compute(person.to_algo_input())
    assert result.value is False


def test_person_input_age_calcule_depuis_birth_date():
    """L'âge est calculé à la volée depuis schema:birthDate, pas passé directement."""
    person = PersonInput(
        cv_nationality="FR",
        schema_birth_date=date(1990, 6, 15),
        cccev_civil_rights_intact=True,
        cccev_electoral_list_registered=True,
    )
    algo_input = person.to_algo_input()
    assert algo_input.data["age"] >= 0


# --- Élections municipales : citoyens UE résidant en France ---

CITOYEN_UE_RESIDENT = PersonInput(
    cv_nationality="DE",
    schema_birth_date=date(1985, 3, 20),
    cccev_civil_rights_intact=True,
    cccev_electoral_list_registered=True,
    cv_domicile_country="FR",
)


def test_citoyen_ue_resident_peut_voter_municipales():
    algo = DroitVoteAlgorithm()
    result = algo.compute(
        CITOYEN_UE_RESIDENT.to_algo_input(context={"type_election": "municipale"})
    )
    assert result.value is True


def test_citoyen_ue_resident_ne_peut_pas_voter_nationales():
    algo = DroitVoteAlgorithm()
    result = algo.compute(
        CITOYEN_UE_RESIDENT.to_algo_input(context={"type_election": "nationale"})
    )
    assert result.value is False


def test_citoyen_ue_non_resident_ne_peut_pas_voter_municipales():
    algo = DroitVoteAlgorithm()
    person = PersonInput(
        cv_nationality="DE",
        schema_birth_date=date(1985, 3, 20),
        cccev_civil_rights_intact=True,
        cccev_electoral_list_registered=True,
        cv_domicile_country="DE",  # réside en Allemagne, pas en France
    )
    result = algo.compute(person.to_algo_input(context={"type_election": "municipale"}))
    assert result.value is False


def test_citoyen_hors_ue_ne_peut_pas_voter_municipales():
    algo = DroitVoteAlgorithm()
    person = PersonInput(
        cv_nationality="MA",  # Maroc — hors UE
        schema_birth_date=date(1985, 3, 20),
        cccev_civil_rights_intact=True,
        cccev_electoral_list_registered=True,
        cv_domicile_country="FR",
    )
    result = algo.compute(person.to_algo_input(context={"type_election": "municipale"}))
    assert result.value is False


def test_type_election_par_defaut_est_nationale():
    """Sans context, le comportement doit être identique à type_election='nationale'."""
    algo = DroitVoteAlgorithm()
    result = algo.compute(CITOYEN_UE_RESIDENT.to_algo_input())
    assert result.value is False
    assert result.metadata["type_election"] == "nationale"