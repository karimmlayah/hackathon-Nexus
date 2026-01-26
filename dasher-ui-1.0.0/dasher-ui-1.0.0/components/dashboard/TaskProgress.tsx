"use client";
//import node modules libraries
import { IconCircleCheck, IconCircleDashedCheck } from "@tabler/icons-react";
import { Row, Col, Card, CardBody } from "react-bootstrap";

//import custom components
import FinFitTippy from "components/common/FinFitTippy";
import CustomProgressBar from "components/common/CustomProgressBar";

const TaskProgress = () => {
  return (
    <Card className="card-lg mb-6">
      <CardBody>
        <div className="mb-4">
          <h5 className="mb-0">Task Progress</h5>
        </div>
        <div className="fs-1 fw-bold mb-3">64%</div>
        <div className="d-flex align-items-center gap-1 w-100 mb-4">
          <div className="w-25">
            <FinFitTippy content="Completed">
              <CustomProgressBar
                className="mb-2"
                now={100}
                style={{ height: "3px" }}
                variant="info-light"
              />
            </FinFitTippy>
            24%
          </div>
          <div className="w-50">
            <FinFitTippy content="In Progress">
              <CustomProgressBar
                className="mb-2"
                now={100}
                style={{ height: "3px" }}
                variant="primary-light"
              />
            </FinFitTippy>
            35%
          </div>
          <div className="w-75">
            <FinFitTippy content="Up Coming">
              <CustomProgressBar
                className="mb-2"
                now={100}
                style={{ height: "3px" }}
                variant="danger-light"
              />
            </FinFitTippy>
            41%
          </div>
        </div>
        <div className="bg-gray-100 p-3 rounded-4">
          <Row className="g-3">
            <Col md={4}>
              <Card className="card-lg">
                <CardBody className="text-center p-3">
                  <div className="icon-shape icon-lg bg-info-subtle text-info-emphasis rounded-pill">
                    <IconCircleCheck size={20} />
                  </div>
                  <div className="lh-1 mt-4">
                    <div className="fs-4 fw-bold mb-1">8</div>
                    <div className="text-secondary small">Completed</div>
                  </div>
                </CardBody>
              </Card>
            </Col>
            <Col md={4}>
              <Card className="card-lg">
                <CardBody className="text-center p-3">
                  <div className="icon-shape icon-lg bg-primary-subtle text-primary-emphasis rounded-pill">
                    <IconCircleCheck size={20} />
                  </div>
                  <div className="lh-1 mt-4">
                    <div className="fs-4 fw-bold mb-1">12</div>
                    <div className="text-secondary small">In-Progress</div>
                  </div>
                </CardBody>
              </Card>
            </Col>
            <Col md={4}>
              <Card className="card-lg">
                <CardBody className="text-center p-3">
                  <div className="icon-shape icon-lg bg-danger-subtle text-danger-emphasis rounded-pill">
                    <IconCircleDashedCheck size={20} />
                  </div>
                  <div className="lh-1 mt-4">
                    <div className="fs-4 fw-bold mb-1">14</div>
                    <div className="text-secondary small">Up Coming</div>
                  </div>
                </CardBody>
              </Card>
            </Col>
          </Row>
        </div>
      </CardBody>
    </Card>
  );
};

export default TaskProgress;

