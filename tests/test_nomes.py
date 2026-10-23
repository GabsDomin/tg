from tg.publicar.exportar import formatar_nome


def test_mantem_algarismos_romanos_e_siglas():
    assert formatar_nome("CAPS AD III PARAISOPOLIS") == "CAPS AD III Paraisópolis"
    assert formatar_nome("CENT DE AT PSIC ALCOOL E DROGA CAPS II ITAPETININGA") == \
        "Centro de Atenção Psicossocial Álcool e Droga CAPS II Itapetininga"


def test_preposicoes_em_minuscula_exceto_no_inicio():
    assert formatar_nome("CENTRO DE ATENCAO PSICOSSOCIAL ALCOOL E DROGAS DE ITANHAEM").endswith("Drogas de Itanhaem")
