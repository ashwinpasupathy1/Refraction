declare module 'plotly.js-dist-min' {
  interface PlotlyHTMLElement extends HTMLDivElement {
    on(event: string, callback: (data: Record<string, unknown>) => void): void;
  }

  interface PlotData {
    [key: string]: unknown;
  }

  interface Layout {
    [key: string]: unknown;
  }

  interface Config {
    responsive?: boolean;
    displayModeBar?: boolean;
    editable?: boolean;
    [key: string]: unknown;
  }

  function newPlot(
    root: HTMLDivElement,
    data: PlotData[],
    layout?: Layout,
    config?: Config
  ): Promise<PlotlyHTMLElement>;

  function react(
    root: HTMLDivElement,
    data: PlotData[],
    layout?: Layout,
    config?: Config
  ): Promise<PlotlyHTMLElement>;

  function purge(root: HTMLDivElement): void;

  export { PlotlyHTMLElement, PlotData, Layout, Config };
  export default { newPlot, react, purge };
}
