"""Testes do ponto de entrada da aplicação (TradutorLegendas26.py)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))


def test_main_restaura_tema_salvo_antes_de_criar_a_interface(mocker):
    """
    Regressão: o tema escolhido pelo usuário voltava sempre para 'escuro' ao reabrir o programa
    porque inicializar_tema() nunca era chamado antes da construção dos widgets.
    """
    import TradutorLegendas26 as ponto_entrada

    ordem = []
    view_falsa = mocker.MagicMock()

    def _criar_interface():
        ordem.append("interface")
        return view_falsa

    mocker.patch.object(
        ponto_entrada, "inicializar_tema", side_effect=lambda: ordem.append("tema")
    )
    mocker.patch.object(ponto_entrada, "OrquestradorTraducoes")
    mocker.patch.object(ponto_entrada, "ControladorApp")
    mocker.patch.object(ponto_entrada, "InterfaceGrafica", side_effect=_criar_interface)

    ponto_entrada.main()

    assert ordem == ["tema", "interface"]
    view_falsa.mainloop.assert_called_once()
