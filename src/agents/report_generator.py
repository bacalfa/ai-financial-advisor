"""
Investment Report Generator Agent.

This agent uses the "investment_report_generation" Agent Skill via Anthropic's
Skills Beta API to generate comprehensive PDF investment analysis reports.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generate professional PDF investment analysis reports.

    This class creates comprehensive reports from investment recommendation data,
    including charts, tables, and formatted text sections.
    """

    def __init__(
        self, output_dir: str = "outputs/reports", temp_dir: str = "outputs/temp"
    ):
        """
        Initialize the report generator.

        Args:
            output_dir: Directory for generated PDF reports
            temp_dir: Directory for temporary chart images
        """
        self.output_dir = Path(output_dir)
        self.temp_dir = Path(temp_dir)

        # Create directories if they don't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Setup styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

        # Color scheme
        self.colors = {
            "primary": colors.HexColor("#1f77b4"),
            "success": colors.HexColor("#2ca02c"),
            "warning": colors.HexColor("#ff7f0e"),
            "danger": colors.HexColor("#d62728"),
            "neutral": colors.HexColor("#7f7f7f"),
        }

        logger.info("Initialized ReportGenerator")

    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Title"],
                fontSize=24,
                textColor=colors.HexColor("#1f77b4"),
                spaceAfter=30,
                alignment=TA_CENTER,
            )
        )

        # Section header style
        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading1"],
                fontSize=16,
                textColor=colors.HexColor("#1f77b4"),
                spaceAfter=12,
                spaceBefore=12,
            )
        )

        # Subsection header style
        self.styles.add(
            ParagraphStyle(
                name="SubsectionHeader",
                parent=self.styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#333333"),
                spaceAfter=10,
                spaceBefore=10,
            )
        )

        # Recommendation style
        self.styles.add(
            ParagraphStyle(
                name="Recommendation",
                parent=self.styles["Normal"],
                fontSize=18,
                textColor=colors.HexColor("#2ca02c"),
                alignment=TA_CENTER,
                spaceAfter=20,
            )
        )

    def generate_report(
        self, recommendation: dict[str, Any], output_filename: str | None = None
    ) -> str:
        """
        Generate comprehensive PDF investment report.

        Args:
            recommendation: Investment recommendation data from FinancialAdvisor
            output_filename: Optional custom filename

        Returns:
            Path to generated PDF report
        """
        try:
            # Generate filename if not provided
            if output_filename is None:
                ticker = recommendation.get("ticker", "UNKNOWN")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"investment_report_{ticker}_{timestamp}.pdf"
                recommendation_filename = f"recommendation_{ticker}_{timestamp}.json"
            else:
                recommendation_filename = output_filename.replace(".pdf", ".json")

            output_path = self.output_dir / output_filename
            recommendation_path = self.temp_dir / recommendation_filename

            with open(recommendation_path, "w") as f:
                json.dump(recommendation, f)

            logger.info(f"Generating report: {output_filename}")

            # Create PDF document
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=letter,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=1 * inch,
                bottomMargin=0.75 * inch,
            )

            # Build report content
            story = []

            # 1. Cover Page
            story.extend(self._create_cover_page(recommendation))
            story.append(PageBreak())

            # 2. Executive Summary
            story.extend(self._create_executive_summary(recommendation))
            story.append(PageBreak())

            # 3. Financial Health Analysis
            story.extend(self._create_financial_analysis(recommendation))
            story.append(PageBreak())

            # 4. Valuation Analysis
            story.extend(self._create_valuation_analysis(recommendation))
            story.append(PageBreak())

            # 5. Technical Analysis
            story.extend(self._create_technical_analysis(recommendation))
            story.append(PageBreak())

            # 6. Risk Assessment
            story.extend(self._create_risk_assessment(recommendation))
            story.append(PageBreak())

            # 7. Conclusion
            story.extend(self._create_conclusion(recommendation))

            # 8. Disclaimer
            story.extend(self._create_disclaimer())

            # Build PDF
            doc.build(
                story,
                onFirstPage=self._add_header_footer,
                onLaterPages=self._add_header_footer,
            )

            logger.info(f"Report generated successfully: {output_path}")

            return str(output_path)

        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}", exc_info=True)
            raise

    def _create_cover_page(self, rec: dict[str, Any]) -> list:
        """Create cover page elements."""
        elements = []

        # Title
        title = Paragraph(
            f"Investment Analysis Report<br/>"
            f"{rec.get('company_name', 'N/A')} ({rec.get('ticker', 'N/A')})",
            self.styles["CustomTitle"],
        )
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(title)
        elements.append(Spacer(1, 0.5 * inch))

        # Recommendation badge
        rec_type = rec.get("recommendation", "HOLD")
        rec_color = self._get_recommendation_color(rec_type)

        rec_style = ParagraphStyle(
            name="RecBadge",
            parent=self.styles["Normal"],
            fontSize=24,
            textColor=rec_color,
            alignment=TA_CENTER,
            spaceAfter=20,
        )

        rec_text = Paragraph(f"<b>{rec_type}</b>", rec_style)
        elements.append(rec_text)
        elements.append(Spacer(1, 0.3 * inch))

        # Key metrics summary
        confidence = rec.get("confidence", 0.0)
        composite_score = rec.get("composite_score", 0.0)

        summary_data = [
            ["Metric", "Value"],
            ["Confidence Level", f"{confidence:.1%}"],
            ["Composite Score", f"{composite_score:.2f}/1.0"],
            ["Report Date", datetime.now().strftime("%Y-%m-%d")],
            ["Analyst", "AI-Powered Financial Advisory System"],
        ]

        summary_table = Table(summary_data, colWidths=[3 * inch, 2.5 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), self.colors["primary"]),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        elements.append(summary_table)

        return elements

    def _create_executive_summary(self, rec: dict[str, Any]) -> list:
        """Create executive summary section."""
        elements = []

        # Section header
        elements.append(Paragraph("Executive Summary", self.styles["SectionHeader"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Investment thesis
        elements.append(Paragraph("<b>Investment Thesis:</b>", self.styles["Heading3"]))

        # Extract key strengths for thesis
        strengths = rec.get("insights", {}).get("strengths", [])[:3]
        for strength in strengths:
            elements.append(Paragraph(f"• {strength}", self.styles["Normal"]))

        elements.append(Spacer(1, 0.2 * inch))

        # Valuation summary table
        rec_models = rec.get("analysis", {}).get("models", {}).get("valuation", {})
        rec_scores = rec.get("scores", {})
        valuation_data = [
            ["Metric", "Value"],
            ["Current Price", f"${rec_models.get('current_price', 0.0):.2f}"],
            ["Fair Value (DCF)", f"${rec_models.get('dcf_fair_value', 0.0):.2f}"],
            ["Upside Potential", f"{rec_models.get('upside_potential', 0.0):.1%}"],
            ["Fundamental Score", f"{rec_scores.get('fundamental', 0.0):.2f}/1.0"],
            ["Technical Score", f"{rec_scores.get('technical', 0.0):.2f}/1.0"],
        ]

        val_table = Table(valuation_data, colWidths=[3 * inch, 2 * inch])
        val_table.setStyle(self._get_standard_table_style())

        elements.append(val_table)
        elements.append(Spacer(1, 0.2 * inch))

        # Risk assessment
        elements.append(
            Paragraph("<b>Risk Assessment:</b> Medium", self.styles["Normal"])
        )

        return elements

    def _create_financial_analysis(self, rec: dict[str, Any]) -> list:
        """Create financial health analysis section."""
        elements = []

        elements.append(
            Paragraph("Financial Health Analysis", self.styles["SectionHeader"])
        )
        elements.append(Spacer(1, 0.2 * inch))

        # Get statements analysis data
        statements = rec.get("analysis", {}).get("statements", {})
        key_metrics = statements.get("key_metrics", {})
        trend_analysis = statements.get("trend_analysis", {})

        # Health score
        health_score = statements.get("health_score", 0.5)
        elements.append(
            Paragraph(
                f"<b>Overall Health Score:</b> {health_score:.2f}/1.0",
                self.styles["Normal"],
            )
        )
        elements.append(Spacer(1, 0.15 * inch))

        # Profitability metrics table
        elements.append(
            Paragraph("Profitability Metrics", self.styles["SubsectionHeader"])
        )

        profit_data = [
            ["Metric", "Value"],
            [
                "Gross Margin",
                f"{key_metrics.get('gross_margin', 0.0):.1%}",
            ],
            [
                "Operating Margin",
                f"{key_metrics.get('operating_margin', 0.0):.1%}",
            ],
            ["Net Margin", f"{key_metrics.get('net_margin', 0.0):.1%}"],
            ["ROE", f"{key_metrics.get('roe', 0.0):.1%}"],
            ["ROA", f"{key_metrics.get('roa', 0.0):.1%}"],
        ]

        profit_table = Table(
            profit_data, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch]
        )
        profit_table.setStyle(self._get_standard_table_style())
        elements.append(profit_table)
        elements.append(Spacer(1, 0.15 * inch))

        # Liquidity & Solvency metrics
        elements.append(
            Paragraph("Liquidity & Solvency", self.styles["SubsectionHeader"])
        )

        liquidity_data = [
            ["Metric", "Value"],
            [
                "Current Ratio",
                f"{key_metrics.get('current_ratio', 0.0):.2f}",
            ],
            ["Quick Ratio", f"{key_metrics.get('quick_ratio', 0.0):.2f}"],
            ["Debt-to-Equity", f"{key_metrics.get('debt_to_equity', 0.0):.2f}"],
            [
                "Interest Coverage",
                f"{key_metrics.get('interest_coverage', 0.0):.2f}x",
            ],
        ]

        liquidity_table = Table(
            liquidity_data, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch]
        )
        liquidity_table.setStyle(self._get_standard_table_style())
        elements.append(liquidity_table)
        elements.append(Spacer(1, 0.15 * inch))

        # Trend analysis table
        elements.append(Paragraph("Trend Analysis", self.styles["SubsectionHeader"]))

        trend_data = [
            ["Metric", "Assessment"],
            [
                "Revenue",
                trend_analysis.get("revenue", "N/A"),
            ],
            ["Profitability", trend_analysis.get("profitability", "N/A")],
            [
                "Liquidity",
                trend_analysis.get("liquidity", "N/A"),
            ],
            [
                "Leverage",
                trend_analysis.get("leverage", "N/A"),
            ],
        ]

        trend_table = Table(trend_data, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch])
        trend_table.setStyle(self._get_standard_table_style())
        elements.append(trend_table)
        elements.append(Spacer(1, 0.15 * inch))

        # Strengths and concerns
        elements.append(Paragraph("Key Strengths", self.styles["SubsectionHeader"]))
        for strength in statements.get("strengths", [])[:5]:
            elements.append(Paragraph(f"• {strength}", self.styles["Normal"]))

        elements.append(Spacer(1, 0.15 * inch))
        elements.append(Paragraph("Key Concerns", self.styles["SubsectionHeader"]))
        for concern in statements.get("concerns", [])[:5]:
            elements.append(Paragraph(f"• {concern}", self.styles["Normal"]))

        return elements

    def _create_valuation_analysis(self, rec: dict[str, Any]) -> list:
        """Create valuation analysis section."""
        elements = []

        elements.append(Paragraph("Valuation Analysis", self.styles["SectionHeader"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Get valuation data
        models = rec.get("analysis", {}).get("models", {})
        valuation = models.get("valuation", {})
        dcf_model = models.get("dcf_model", {})

        # DCF Summary
        elements.append(Paragraph("DCF Model Summary", self.styles["SubsectionHeader"]))

        dcf_data = [
            ["Component", "Value"],
            [
                "Enterprise Value",
                f"${dcf_model.get('enterprise_value', 0.0) / 1e0:.2f}B",
            ],
            ["Equity Value", f"${dcf_model.get('equity_value', 0.0) / 1e0:.2f}B"],
            ["Fair Value Per Share", f"${valuation.get('dcf_fair_value', 0.0):.2f}"],
            ["Current Price", f"${valuation.get('current_price', 0.0):.2f}"],
            ["Upside/(Downside)", f"{valuation.get('upside_potential', 0.0):.1%}"],
        ]

        dcf_table = Table(dcf_data, colWidths=[3 * inch, 2 * inch])
        dcf_table.setStyle(self._get_standard_table_style())
        elements.append(dcf_table)
        elements.append(Spacer(1, 0.15 * inch))

        # Key Assumptions
        elements.append(Paragraph("Key Assumptions", self.styles["SubsectionHeader"]))

        assumptions_data = [
            ["Assumption", "Value"],
            ["WACC", f"{dcf_model.get('wacc', 0.0):.1%}"],
            ["Terminal Growth Rate", f"{dcf_model.get('terminal_growth', 0.0):.1%}"],
            ["Tax Rate", f"{models.get('assumptions', {}).get('tax_rate', 0.0):.1%}"],
        ]

        assumptions_table = Table(assumptions_data, colWidths=[3 * inch, 2 * inch])
        assumptions_table.setStyle(self._get_standard_table_style())
        elements.append(assumptions_table)
        elements.append(Spacer(1, 0.15 * inch))

        # Comparable analysis if available
        comp_analysis = models.get("comparable_analysis", {})
        if comp_analysis:
            elements.append(
                Paragraph(
                    "Comparable Company Analysis", self.styles["SubsectionHeader"]
                )
            )

            comp_data = [
                ["Multiple", "Peer Average", "Target Company"],
                [
                    "P/E Ratio",
                    f"{comp_analysis.get('peer_average_pe', 0.0):.1f}x",
                    "N/A",
                ],
                [
                    "EV/EBITDA",
                    f"{comp_analysis.get('peer_average_ev_ebitda', 0.0):.1f}x",
                    "N/A",
                ],
            ]

            comp_table = Table(
                comp_data, colWidths=[2 * inch, 1.75 * inch, 1.75 * inch]
            )
            comp_table.setStyle(self._get_standard_table_style())
            elements.append(comp_table)

        return elements

    def _create_technical_analysis(self, rec: dict[str, Any]) -> list:
        """Create technical analysis section."""
        elements = []

        elements.append(Paragraph("Technical Analysis", self.styles["SectionHeader"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Get technical data
        technical = rec.get("analysis", {}).get("technical", {})
        signals = technical.get("signals", {})
        indicators = technical.get("indicators", {})

        # Technical overview
        tech_score = technical.get("technical_score", 0.5)
        elements.append(
            Paragraph(
                f"<b>Technical Score:</b> {tech_score:.2f}/1.0", self.styles["Normal"]
            )
        )
        elements.append(Spacer(1, 0.15 * inch))

        # Signal summary
        elements.append(Paragraph("Signal Summary", self.styles["SubsectionHeader"]))

        signal_data = [
            ["Signal Type", "Status"],
            ["Trend", signals.get("trend", "neutral").capitalize()],
            ["Momentum", signals.get("momentum", "neutral").capitalize()],
            ["Volume", signals.get("volume", "neutral").capitalize()],
            ["Volatility", signals.get("volatility", "medium").capitalize()],
        ]

        signal_table = Table(signal_data, colWidths=[2.5 * inch, 2.5 * inch])
        signal_table.setStyle(self._get_standard_table_style())
        elements.append(signal_table)
        elements.append(Spacer(1, 0.15 * inch))

        # Key indicators
        elements.append(
            Paragraph("Key Technical Indicators", self.styles["SubsectionHeader"])
        )

        sma_keys = [
            ind for ind in indicators if ind.startswith("sma_") and ind[-1].isdigit()
        ]

        indicator_data = [
            ["Indicator", "Value", "Signal"],
            [
                "RSI (14)",
                f"{indicators.get('rsi_14', 50.0):.1f}",
                indicators.get("rsi_signal", "neutral").capitalize(),
            ],
            [
                "MACD",
                f"{indicators.get('macd', 0.0):.2f}",
                indicators.get("macd_crossover", "neutral").capitalize(),
            ],
            # ["SMA 20", f"${indicators.get('sma_20', 0.0):.2f}", ""],
            # ["SMA 50", f"${indicators.get('sma_50', 0.0):.2f}", ""],
            # ["SMA 200", f"${indicators.get('sma_200', 0.0):.2f}", ""],
        ]
        [
            indicator_data.append(
                [
                    f"SMA {sma_key.split('_')[-1]}",
                    f"${indicators.get(sma_key, 0.0):.2f}",
                    "",
                ]
            )
            for sma_key in sma_keys
        ]

        indicator_table = Table(
            indicator_data, colWidths=[2 * inch, 1.75 * inch, 1.75 * inch]
        )
        indicator_table.setStyle(self._get_standard_table_style())
        elements.append(indicator_table)
        elements.append(Spacer(1, 0.15 * inch))

        # Support/Resistance levels
        support_resistance = technical.get("support_resistance", {})
        if support_resistance:
            elements.append(
                Paragraph(
                    "Support & Resistance Levels", self.styles["SubsectionHeader"]
                )
            )

            sr_data = [["Level Type", "Prices"]]

            resistance = support_resistance.get("key_resistance", [])
            if resistance:
                sr_data.append(
                    ["Resistance", ", ".join([f"${r:.2f}" for r in resistance])]
                )

            support = support_resistance.get("key_support", [])
            if support:
                sr_data.append(["Support", ", ".join([f"${s:.2f}" for s in support])])

            sr_table = Table(sr_data, colWidths=[2 * inch, 3.5 * inch])
            sr_table.setStyle(self._get_standard_table_style())
            elements.append(sr_table)

        # Trading setup if available
        trading_setup = technical.get("trading_setup", {})
        if trading_setup and trading_setup.get("bias") != "neutral":
            elements.append(Spacer(1, 0.15 * inch))
            elements.append(
                Paragraph("Recommended Trading Setup", self.styles["SubsectionHeader"])
            )

            bias = trading_setup.get("bias", "neutral")
            entry_points = trading_setup.get("entry_points", [])
            stop_loss = trading_setup.get("stop_loss", 0.0)
            targets = trading_setup.get("targets", [])

            setup_text = f"<b>Bias:</b> {bias.capitalize()}<br/>"
            if entry_points:
                setup_text += f"<b>Entry Points:</b> {', '.join([f'${e:.2f}' for e in entry_points])}<br/>"
            if stop_loss:
                setup_text += f"<b>Stop Loss:</b> ${stop_loss:.2f}<br/>"
            if targets:
                setup_text += (
                    f"<b>Targets:</b> {', '.join([f'${t:.2f}' for t in targets])}"
                )

            elements.append(Paragraph(setup_text, self.styles["Normal"]))

        return elements

    def _create_risk_assessment(self, rec: dict[str, Any]) -> list:
        """Create risk assessment section."""
        elements = []

        elements.append(Paragraph("Risk Assessment", self.styles["SectionHeader"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Aggregate risks from all analyses
        all_risks = []

        statements = rec.get("analysis", {}).get("statements", {})
        all_risks.extend(statements.get("risks", []))

        models = rec.get("analysis", {}).get("models", {})
        all_risks.extend(models.get("risks", []))

        technical = rec.get("analysis", {}).get("technical", {})
        all_risks.extend(technical.get("risks", []))

        # Deduplicate and limit
        unique_risks = list(set(all_risks))[:5]

        elements.append(Paragraph("Key Risk Factors", self.styles["SubsectionHeader"]))

        for i, risk in enumerate(unique_risks, 1):
            elements.append(Paragraph(f"{i}. {risk}", self.styles["Normal"]))

        if not unique_risks:
            elements.append(
                Paragraph(
                    "No significant risk factors identified.", self.styles["Normal"]
                )
            )

        return elements

    def _create_conclusion(self, rec: dict[str, Any]) -> list:
        """Create conclusion section."""
        elements = []

        elements.append(
            Paragraph("Conclusion & Recommendation", self.styles["SectionHeader"])
        )
        elements.append(Spacer(1, 0.2 * inch))

        # Restate recommendation
        rec_type = rec.get("recommendation", "HOLD")
        confidence = rec.get("confidence", 0.0)

        conclusion_text = f"""
        Based on comprehensive analysis across fundamental, valuation, and technical dimensions,
        our recommendation is <b>{rec_type}</b> with a confidence level of {confidence:.1%}.
        """

        elements.append(Paragraph(conclusion_text, self.styles["Normal"]))
        elements.append(Spacer(1, 0.15 * inch))

        # Key supporting points
        elements.append(
            Paragraph("Key Supporting Points:", self.styles["SubsectionHeader"])
        )

        strengths = rec.get("insights", []).get("strengths", [])[:3]
        for strength in strengths:
            elements.append(Paragraph(f"• {strength}", self.styles["Normal"]))

        return elements

    def _create_disclaimer(self) -> list:
        """Create disclaimer section."""
        elements = []

        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("Disclaimer", self.styles["SubsectionHeader"]))

        disclaimer_text = """
        <b>IMPORTANT DISCLAIMER:</b><br/><br/>
        
        This report has been generated by an AI-powered financial advisory system and is provided 
        for informational purposes only. This report does not constitute financial, investment, 
        tax, or legal advice, and should not be relied upon as such.<br/><br/>
        
        The analysis, recommendations, and projections contained in this report are based on 
        data and assumptions that may or may not prove to be accurate. Past performance is not 
        indicative of future results. Investment in securities involves risk, including the 
        possible loss of principal.<br/><br/>
        
        Before making any investment decision, you should consult with a qualified financial 
        advisor, accountant, or attorney who can evaluate your individual circumstances and 
        objectives. The creators and operators of this AI system assume no liability for any 
        investment decisions made based on this report.<br/><br/>
        
        Data sources: Market data retrieved from public APIs (yfinance) and SEC filings. 
        Analysis performed using Agent Skills framework by Anthropic.
        """

        disclaimer_style = ParagraphStyle(
            name="Disclaimer",
            parent=self.styles["Normal"],
            fontSize=9,
            textColor=colors.grey,
        )

        elements.append(Paragraph(disclaimer_text, disclaimer_style))

        return elements

    def _get_standard_table_style(self) -> TableStyle:
        """Get standard table styling."""
        return TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), self.colors["primary"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )

    def _get_recommendation_color(self, rec_type: str):
        """Get color for recommendation type."""
        if rec_type in ["STRONG_BUY", "BUY"]:
            return self.colors["success"]
        elif rec_type in ["STRONG_SELL", "SELL"]:
            return self.colors["danger"]
        else:
            return self.colors["neutral"]

    def _add_header_footer(self, canvas, doc):
        """Add header and footer to each page."""
        canvas.saveState()

        # Footer
        footer_text = f"Generated by AI-Powered Financial Advisory System | {datetime.now().strftime('%Y-%m-%d')}"
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(letter[0] / 2.0, 0.5 * inch, footer_text)

        # Page number
        page_num = f"Page {canvas.getPageNumber()}"
        canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, page_num)

        canvas.restoreState()
