//import node module libraries
import { Fragment } from "react";
import { Metadata } from "next";
import { Col, Row } from "react-bootstrap";

//import custom components
import DashboardStats from "components/dashboard/DashboardStats";
import ActiveProject from "components/dashboard/ActiveProject";
import TaskProgress from "components/dashboard/TaskProgress";
import AIBanner from "components/dashboard/AIBanner";


export const metadata: Metadata = {
  title: "Project Dashboard | FinFit - Responsive Bootstrap 5 Admin Dashboard",
  description: "FinFit - Responsive Bootstrap 5 Admin Dashboard",
};

const HomePage = () => {
  return (
    <Fragment>
      <Row className="g-6 mb-6">
        <DashboardStats />
      </Row>
      <Row className="g-6 mb-6">
        <Col xl={8}>
          <ActiveProject />
        </Col>
        <Col xl={4}>
          <TaskProgress />
          <AIBanner />

        </Col>
      </Row>
    </Fragment>
  );
};

export default HomePage;
