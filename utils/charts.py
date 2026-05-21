import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

PALETTE = {
    "blue":   "#185FA5",
    "blue2":  "#378ADD",
    "teal":   "#1D9E75",
    "teal2":  "#5DCAA5",
    "purple": "#534AB7",
    "pink":   "#993556",
    "amber":  "#854F0B",
    "amber2": "#EF9F27",
    "red":    "#E24B4A",
    "gray":   "#888780",
}

LAYOUT_BASE = dict(
    font=dict(family="IBM Plex Sans, sans-serif", size=11, color="#444441"),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        font=dict(size=10), bgcolor="rgba(0,0,0,0)"
    ),
    xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
    yaxis=dict(gridcolor="#f1efe8", linecolor="#e8e4dc", tickfont=dict(size=10), zeroline=False),
    hoverlabel=dict(bgcolor="white", bordercolor="#e8e4dc", font_size=11),
)

def bar_chart(x, y, color="blue", title="", ylabel="", neg_color="red", show_values=True):
    colors = [PALETTE[neg_color] if v < 0 else PALETTE[color] for v in y]
    fig = go.Figure(go.Bar(
        x=x, y=y,
        marker_color=colors,
        text=[f"{v:.1f}" for v in y] if show_values else None,
        textposition="outside",
        textfont=dict(size=9, color="#444441"),
        hovertemplate="%{x}: <b>%{y:.2f}</b><extra></extra>",
    ))
    fig.update_layout(**LAYOUT_BASE, height=280)
    fig.update_layout(
        yaxis_title=ylabel,
        shapes=[dict(type="line", x0=0, x1=1, xref="paper", y0=0, y1=0,
                     line=dict(color="#D3D1C7", width=1))]
    )
    return fig

def line_chart(series: dict, x, ylabel="", dashes=None):
    fig = go.Figure()
    palette_vals = list(PALETTE.values())
    for i, (name, y) in enumerate(series.items()):
        dash = "dash" if dashes and name in dashes else "solid"
        fig.add_trace(go.Scatter(
            x=x, y=y, name=name,
            mode="lines+markers",
            line=dict(color=palette_vals[i % len(palette_vals)], width=2, dash=dash),
            marker=dict(size=4),
            hovertemplate=f"{name}: <b>%{{y:.2f}}</b><extra></extra>",
        ))
    fig.update_layout(**LAYOUT_BASE, height=280, yaxis_title=ylabel)
    return fig

def stacked_bar(x, series: dict, ylabel="", colors=None):
    fig = go.Figure()
    pal = colors or list(PALETTE.values())
    for i, (name, y) in enumerate(series.items()):
        fig.add_trace(go.Bar(
            name=name, x=x, y=y,
            marker_color=pal[i % len(pal)],
            hovertemplate=f"{name}: <b>%{{y:.2f}}</b><extra></extra>",
        ))
    fig.update_layout(**LAYOUT_BASE, height=280, barmode="stack", yaxis_title=ylabel)
    return fig

def area_chart(series: dict, x, ylabel=""):
    fig = go.Figure()
    palette_vals = list(PALETTE.values())
    for i, (name, y) in enumerate(series.items()):
        c = palette_vals[i % len(palette_vals)]
        fig.add_trace(go.Scatter(
            x=x, y=y, name=name,
            fill="tozeroy" if i == 0 else "tonexty",
            mode="lines",
            line=dict(color=c, width=1.5),
            fillcolor=c.replace("#", "rgba(").replace(")", ",0.12)") if "#" in c else c,
            hovertemplate=f"{name}: <b>%{{y:.2f}}</b><extra></extra>",
        ))
    fig.update_layout(**LAYOUT_BASE, height=280, yaxis_title=ylabel)
    return fig
