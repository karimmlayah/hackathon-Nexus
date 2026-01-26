//import node module libraries
import { Fragment } from "react";
import { Metadata } from "next";
import { Col, Row } from "react-bootstrap";

//import custom components
import DashboardStats from "components/dashboard/DashboardStats";
import ActiveProject from "components/dashboard/ActiveProject";
import TaskProgress from "components/dashboard/TaskProgress";
import TeamsTable from "components/dashboard/TeamsTable";
import AIBanner from "components/dashboard/AIBanner";
import ActivityLog from "components/dashboard/ActivityLog";
import ProjectBudget from "components/dashboard/ProjectBudget";
import TaskList from "components/dashboard/TaskList";
import UpcomingMeetingSlider from "components/dashboard/UpcomingMeetingSlider";

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
          <TeamsTable />
          <ActivityLog />
          <TaskList />
        </Col>
        <Col xl={4}>
          <TaskProgress />
          <AIBanner />
          <ProjectBudget />
          <UpcomingMeetingSlider />
        </Col>
      </Row>
    </Fragment>
  );
};

export default HomePage;
