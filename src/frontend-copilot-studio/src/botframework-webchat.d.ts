declare module "botframework-webchat" {
  import { ComponentType } from "react";

  interface DirectLine {
    postActivity: (activity: unknown) => unknown;
    activity$: unknown;
    connectionStatus$: unknown;
    end: () => void;
  }

  interface StyleOptions {
    rootHeight?: string;
    rootWidth?: string;
    bubbleBackground?: string;
    bubbleFromUserBackground?: string;
    sendBoxButtonColor?: string;
    primaryFont?: string;
    [key: string]: unknown;
  }

  interface WebChatProps {
    directLine: DirectLine;
    styleOptions?: StyleOptions;
    locale?: string;
    [key: string]: unknown;
  }

  export function createDirectLine(options: {
    token: string;
    domain?: string;
  }): DirectLine;

  const ReactWebChat: ComponentType<WebChatProps>;
  export default ReactWebChat;
}
