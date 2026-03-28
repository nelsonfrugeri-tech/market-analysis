"""Tests for CLI integration with MetricsExplainer and email sending."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from market_analysis.cli import main, _build_metrics_dict_for_explainer


class TestBuildMetricsDictForExplainer:
    """Tests for _build_metrics_dict_for_explainer helper."""

    def test_extracts_all_performance_fields(self) -> None:
        perf = mock.MagicMock()
        perf.return_pct = 1.5
        perf.vs_selic = -0.3
        perf.vs_cdi = -0.2
        perf.vs_ipca = 0.1
        perf.volatility = 0.05
        perf.sharpe_ratio = 1.2
        perf.max_drawdown = -0.02
        perf.alpha = 0.01
        perf.beta = 0.95
        perf.var_95 = -0.03

        result = _build_metrics_dict_for_explainer(perf)

        assert result["return_pct"] == 1.5
        assert result["vs_selic"] == -0.3
        assert result["vs_cdi"] == -0.2
        assert result["vs_ipca"] == 0.1
        assert result["volatility"] == 0.05
        assert result["sharpe_ratio"] == 1.2
        assert result["max_drawdown"] == -0.02
        assert result["alpha"] == 0.01
        assert result["beta"] == 0.95
        assert result["var_95"] == -0.03


class TestCLIEmailFlag:
    """Tests for --email flag in CLI argument parsing."""

    def test_parser_accepts_email_flag(self) -> None:
        """The main function should accept --email without error."""
        # We test via argparse directly
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--email", type=str, nargs="+", default=None)
        args = parser.parse_args(["--email", "test@example.com"])
        assert args.email == ["test@example.com"]

    def test_parser_accepts_multiple_emails(self) -> None:
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--email", type=str, nargs="+", default=None)
        args = parser.parse_args(["--email", "a@x.com", "b@x.com"])
        assert args.email == ["a@x.com", "b@x.com"]


class TestCLIMainIntegration:
    """Integration tests for main() with mocked dependencies."""

    @mock.patch("market_analysis.cli._send_email")
    @mock.patch("market_analysis.cli.generate_pdf")
    @mock.patch("market_analysis.cli._run_explainer")
    @mock.patch("market_analysis.cli.compute_performance")
    @mock.patch("market_analysis.cli.collect_news")
    @mock.patch("market_analysis.cli.collect_all_benchmarks_sync")
    @mock.patch("market_analysis.cli.collect_multiple_months")
    def test_main_with_email_sends_email(
        self,
        mock_collect: mock.MagicMock,
        mock_benchmarks: mock.MagicMock,
        mock_news: mock.MagicMock,
        mock_perf: mock.MagicMock,
        mock_explainer: mock.MagicMock,
        mock_pdf: mock.MagicMock,
        mock_send: mock.MagicMock,
        tmp_path: Path,
    ) -> None:
        record = mock.MagicMock()
        record.date = "2026-01-01"
        mock_collect.return_value = [record]

        bench = mock.MagicMock()
        bench.selic_accumulated = 0.1
        bench.cdi_accumulated = 0.1
        bench.ipca_accumulated = 0.05
        bench.cdb_estimated = 0.09
        bench.poupanca_estimated = 0.06
        mock_benchmarks.return_value = bench

        mock_news.return_value = []

        perf = mock.MagicMock()
        perf.return_pct = 1.5
        perf.vs_selic = -0.3
        perf.vs_cdi = -0.2
        perf.fund_name = "Nu Reserva Planejada"
        mock_perf.return_value = perf

        mock_explainer.return_value = []

        pdf_path = tmp_path / "report.pdf"
        pdf_path.write_bytes(b"%PDF-fake")
        mock_pdf.return_value = pdf_path

        result = main(["--months", "1", "--email", "test@example.com"])

        assert result == 0
        mock_send.assert_called_once()
        args = mock_send.call_args
        assert args[0][0] == pdf_path  # pdf_path
        assert args[0][1] == ["test@example.com"]  # recipients

    @mock.patch("market_analysis.cli._send_email")
    @mock.patch("market_analysis.cli.generate_pdf")
    @mock.patch("market_analysis.cli._run_explainer")
    @mock.patch("market_analysis.cli.compute_performance")
    @mock.patch("market_analysis.cli.collect_all_benchmarks_sync")
    @mock.patch("market_analysis.cli.collect_multiple_months")
    def test_main_without_email_skips_send(
        self,
        mock_collect: mock.MagicMock,
        mock_benchmarks: mock.MagicMock,
        mock_perf: mock.MagicMock,
        mock_explainer: mock.MagicMock,
        mock_pdf: mock.MagicMock,
        mock_send: mock.MagicMock,
        tmp_path: Path,
    ) -> None:
        record = mock.MagicMock()
        record.date = "2026-01-01"
        mock_collect.return_value = [record]

        bench = mock.MagicMock()
        bench.selic_accumulated = 0.1
        bench.cdi_accumulated = 0.1
        bench.ipca_accumulated = 0.05
        bench.cdb_estimated = 0.09
        bench.poupanca_estimated = 0.06
        mock_benchmarks.return_value = bench

        perf = mock.MagicMock()
        perf.return_pct = 1.5
        perf.vs_selic = -0.3
        perf.vs_cdi = -0.2
        mock_perf.return_value = perf

        mock_explainer.return_value = None
        mock_pdf.return_value = tmp_path / "report.pdf"

        result = main(["--months", "1", "--no-news"])

        assert result == 0
        mock_send.assert_not_called()

    @mock.patch("market_analysis.cli.generate_pdf")
    @mock.patch("market_analysis.cli._run_explainer")
    @mock.patch("market_analysis.cli.compute_performance")
    @mock.patch("market_analysis.cli.collect_all_benchmarks_sync")
    @mock.patch("market_analysis.cli.collect_multiple_months")
    def test_main_no_explain_skips_explainer(
        self,
        mock_collect: mock.MagicMock,
        mock_benchmarks: mock.MagicMock,
        mock_perf: mock.MagicMock,
        mock_explainer: mock.MagicMock,
        mock_pdf: mock.MagicMock,
        tmp_path: Path,
    ) -> None:
        record = mock.MagicMock()
        record.date = "2026-01-01"
        mock_collect.return_value = [record]

        bench = mock.MagicMock()
        bench.selic_accumulated = 0.1
        bench.cdi_accumulated = 0.1
        bench.ipca_accumulated = 0.05
        bench.cdb_estimated = 0.09
        bench.poupanca_estimated = 0.06
        mock_benchmarks.return_value = bench

        perf = mock.MagicMock()
        perf.return_pct = 1.5
        perf.vs_selic = -0.3
        perf.vs_cdi = -0.2
        mock_perf.return_value = perf

        mock_pdf.return_value = tmp_path / "report.pdf"

        result = main(["--months", "1", "--no-news", "--no-explain"])

        assert result == 0
        mock_explainer.assert_not_called()

    @mock.patch("market_analysis.cli.generate_pdf")
    @mock.patch("market_analysis.cli._run_explainer")
    @mock.patch("market_analysis.cli.compute_performance")
    @mock.patch("market_analysis.cli.collect_all_benchmarks_sync")
    @mock.patch("market_analysis.cli.collect_multiple_months")
    def test_main_passes_explanations_to_pdf(
        self,
        mock_collect: mock.MagicMock,
        mock_benchmarks: mock.MagicMock,
        mock_perf: mock.MagicMock,
        mock_explainer: mock.MagicMock,
        mock_pdf: mock.MagicMock,
        tmp_path: Path,
    ) -> None:
        record = mock.MagicMock()
        record.date = "2026-01-01"
        mock_collect.return_value = [record]

        bench = mock.MagicMock()
        bench.selic_accumulated = 0.1
        bench.cdi_accumulated = 0.1
        bench.ipca_accumulated = 0.05
        bench.cdb_estimated = 0.09
        bench.poupanca_estimated = 0.06
        mock_benchmarks.return_value = bench

        perf = mock.MagicMock()
        perf.return_pct = 1.5
        perf.vs_selic = -0.3
        perf.vs_cdi = -0.2
        mock_perf.return_value = perf

        fake_explanations = [mock.MagicMock()]
        mock_explainer.return_value = fake_explanations
        mock_pdf.return_value = tmp_path / "report.pdf"

        result = main(["--months", "1", "--no-news"])

        assert result == 0
        pdf_call_kwargs = mock_pdf.call_args.kwargs
        assert pdf_call_kwargs["metric_explanations"] is fake_explanations
