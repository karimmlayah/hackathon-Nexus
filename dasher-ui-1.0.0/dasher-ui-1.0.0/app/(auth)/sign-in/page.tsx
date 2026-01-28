"use client";

//import node modules libraries
import { Fragment, useState } from "react";
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
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  IconBrandFacebookFilled,
  IconBrandGoogleFilled,
  IconEyeOff,
} from "@tabler/icons-react";

//import custom components
import Flex from "components/common/Flex";
import { getAssetPath } from "helper/assetPath";

const SignIn = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnTo = searchParams.get("returnTo");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch("http://127.0.0.1:8000/api/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem("finfit_token", data.access_token);
        if (returnTo) {
          window.location.href = `${returnTo}?token=${data.access_token}`;
        } else {
          router.push("/");
        }
      } else {
        setError(data.detail || "Login failed");
      }
    } catch (err: unknown) {
      setError("Server connection failed");
    } finally {
      setLoading(false);
    }
  };
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
              <Link href="/sign-up" className="text-primary ms-1">
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
              <Form className="mb-6" onSubmit={handleSignIn}>
                {error && <div className="alert alert-danger mb-4">{error}</div>}
                <div className="mb-3">
                  <FormLabel htmlFor="signinEmailInput">
                    Email <span className="text-danger">*</span>
                  </FormLabel>
                  <FormControl
                    type="email"
                    id="signinEmailInput"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                  <Feedback type="invalid">Please enter email.</Feedback>
                </div>
                <div className="mb-3">
                  <FormLabel htmlFor="formSignUpPassword">Password</FormLabel>
                  <div className="password-field position-relative">
                    <FormControl
                      type="password"
                      id="formSignUpPassword"
                      className="fakePassword"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
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
                  <Button variant="primary" type="submit" disabled={loading}>
                    {loading ? "Signing In..." : "Sign In"}
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

