//import node modules libraries
import { Fragment } from "react";
import { Metadata } from "next";

//import custom components
import UserListing from "components/users/UserListing";
import FinFitBreadcrumb from "components/common/FinFitBreadcrumb";
import { Row, Col } from "react-bootstrap";

export const metadata: Metadata = {
  title: "User List | FinFit Dashboard",
  description: "Manage system users",
};

const Blog = () => {
  return (
    <Fragment>
      <Row className="mb-8">
        <Col>
          <h1 className="mb-3 h2">User Management</h1>
          <FinFitBreadcrumb />
        </Col>
      </Row>
      <UserListing />
    </Fragment>
  );
};

export default Blog;

