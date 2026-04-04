/// <reference types="react-scripts" />

declare module "*.css" {
  const content: Record<string, string>;
  export default content;
}

declare module "*.svg" {
  const ReactComponent: React.FunctionComponent<React.SVGAttributes<SVGElement>>;
  export { ReactComponent };
  const src: string;
  export default src;
}
