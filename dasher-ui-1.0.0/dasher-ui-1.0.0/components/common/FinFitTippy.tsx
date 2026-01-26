//import node modules libraries
import React, { ReactNode } from "react";
import { OverlayTrigger, Tooltip } from "react-bootstrap";

interface FinFitTippyProps {
  content: string | ReactNode;
  children: ReactNode;
  placement?: "top" | "right" | "bottom" | "left";
  delayShow?: number;
  delayHide?: number;
  id?: string;
}

const FinFitTippy: React.FC<FinFitTippyProps> = ({
  content,
  children,
  placement = "top",
  delayShow = 250,
  delayHide = 400,
  id = "custom-tooltip",
}) => {
  return (
    <OverlayTrigger
      placement={placement}
      delay={{ show: delayShow, hide: delayHide }}
      overlay={<Tooltip id={id}>{content}</Tooltip>}
    >
      <span style={{ cursor: "pointer" }}>{children}</span>
    </OverlayTrigger>
  );
};

export default FinFitTippy;

