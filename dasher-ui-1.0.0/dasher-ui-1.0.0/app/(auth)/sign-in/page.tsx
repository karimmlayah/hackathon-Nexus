//import node modules libraries
import { Fragment } from "react";
import Feedback from "react-bootstrap/Feedback";
import {
  Row,
  Col,
  Image,
  Card,
  CardBody,
  Form,
  FormLabel,
  FormControl,
  FormCheck,
  Button,
} from "react-bootstrap";
import { Metadata } from "next";
import Link from "next/link";
import {
  IconBrandFacebookFilled,
  IconBrandGoogleFilled,
  IconEyeOff,
} from "@tabler/icons-react";

//import custom components
import Flex from "components/common/Flex";
import { getAssetPath } from "helper/assetPath";

export const metadata: Metadata = {
  title: "Sign In | FinFit - Responsive Bootstrap 5 Admin Dashboard",
  description: "FinFit - Responsive Bootstrap 5 Admin Dashboard",
};

const SignIn = () => {
  return (
    <Fragment>
      <Row className="mb-8">
        <Col xl={{ span: 4, offset: 4 }} md={12}>
          <div className="text-center">
            <Link
              href="/"
              className="fs-2 fw-bold d-flex align-items-center gap-2 justify-content-center mb-6"
            >
              <Image src={getAssetPath("/images/brand/logo/logo-icon.svg")} alt="FinFit" />
              <span>FinFit</span>
            </Link>
            <h1 className="mb-1">Welcome Back</h1>
            <p className="mb-0">
              Don’t have an account yet?
              <Link href="#" className="text-primary ms-1">
                Register here
              </Link>
            </p>
          </div>
        </Col>
      </Row>

      {/* Form Start */}
      <Row className="justify-content-center">
        <Col xl={5} lg={6} md={8}>
          <Card className="card-lg mb-6">
            <CardBody className="p-6">
              <Form className="mb-6">
                <div className="mb-3">
                  <FormLabel htmlFor="signinEmailInput">
                    Email <span className="text-danger">*</span>
                  </FormLabel>
                  <FormControl type="email" id="signinEmailInput" />
                  <Feedback type="invalid">Please enter email.</Feedback>
                </div>
                <div className="mb-3">
                  <FormLabel htmlFor="formSignUpPassword">Password</FormLabel>
                  <div className="password-field position-relative">
                    <FormControl
                      type="password"
                      id="formSignUpPassword"
                      className="fakePassword"
                    />
                    <span>
                      <IconEyeOff className="passwordToggler" size={16} />
                    </span>
                  </div>
                  <Feedback type="invalid">Please enter password.</Feedback>
                </div>
                <Flex
                  className="mb-4"
                  alignItems="center"
                  justifyContent="between"
                >
                  <FormCheck label="Remember me" type="checkbox" />
                  <div>
                    <Link href="" className="text-primary">
                      Forgot Password
                    </Link>
                  </div>
                </Flex>
                <div className="d-grid">
                  <Button variant="primary" type="button">
                    Sign In
                  </Button>
                </div>
              </Form>

              <span>Sign in with your social network.</span>
              <Flex justifyContent="between" className="mt-3 d-flex gap-2">
                <Button href="#" variant="google" className="w-100">
                  <span className="me-3">
                    <IconBrandGoogleFilled size={18} />
                  </span>
                  Continue with Google
                </Button>
                <Button href="#" variant="facebook" className="w-100">
                  <span className="me-3">
                    <IconBrandFacebookFilled size={18} />
                  </span>
                  Continue with Facebook
                </Button>
              </Flex>
            </CardBody>
          </Card>
        </Col>
      </Row>
    </Fragment>
  );
};

export default SignIn;

