"use client";
//import node module libraries
import React, { Fragment, useState } from "react";
import Link from "next/link";
import { useMediaQuery } from "react-responsive";
import {
  IconArrowBarLeft,
  IconArrowBarRight,
  IconMenu2,
  IconSearch,
  IconWorld,
} from "@tabler/icons-react";
import { Container, ListGroup, Navbar, Button } from "react-bootstrap";

//import custom components
import UserMenu from "./UserMenu";
import Flex from "components/common/Flex";
import OffcanvasSidebar from "layouts/OffcanvasSidebar";

//import custom hooks
import useMenu from "hooks/useMenu";

const Header = () => {
  const { toggleMenuHandler, handleCollapsed } = useMenu();

  const isTablet = useMediaQuery({ maxWidth: 990 });

  return (
    <Fragment>
      <Navbar expand="lg" className="navbar-glass px-0 px-lg-4">
        <Container fluid className="px-lg-0">
          <Flex alignItems="center" className="gap-4">
            {isTablet && (
              <div
                className="d-block d-lg-none"
                style={{ cursor: "pointer" }}
                onClick={() => toggleMenuHandler(true)}
              >
                <IconMenu2 size={24} />
              </div>
            )}
            {isTablet || (
              <div>
                <Link href={"#"} className="sidebar-toggle d-flex p-3">
                  <span
                    className="collapse-mini"
                    onClick={() => handleCollapsed("expanded")}
                  >
                    <IconArrowBarLeft
                      size={20}
                      strokeWidth={1.5}
                      className="text-secondary"
                    />
                  </span>
                  <span
                    className="collapse-expanded"
                    onClick={() => handleCollapsed("collapsed")}
                  >
                    <IconArrowBarRight
                      size={20}
                      strokeWidth={1.5}
                      className="text-secondary"
                    />
                  </span>
                </Link>
              </div>
            )}
          </Flex>
          <ListGroup
            bsPrefix="list-unstyled"
            as={"ul"}
            className="d-flex align-items-center mb-0 gap-2"
          >
            <ListGroup.Item as="li">
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  const token = localStorage.getItem("finfit_token");
                  const url = token ? `http://localhost:8000/?token=${token}` : "http://localhost:8000/";
                  window.open(url, "_blank");
                }}
                className="btn btn-primary d-flex align-items-center gap-2 mb-0"
              >
                <IconWorld size={18} />
                <span className="d-none d-md-block">Site Web</span>
              </a>
            </ListGroup.Item>

            <ListGroup.Item as="li" className="d-none d-md-block">
              <div className="input-group">
                <span className="input-group-text bg-white border-end-0">
                  <IconSearch size={16} className="text-muted" />
                </span>
                <input
                  type="text"
                  className="form-control border-start-0 ps-0"
                  placeholder="Search..."
                  aria-label="Search"
                  style={{ maxWidth: '200px' }}
                />
              </div>
            </ListGroup.Item>

            <ListGroup.Item as="li">
              <UserMenu />
            </ListGroup.Item>
          </ListGroup>
        </Container>
      </Navbar>
      {isTablet && <OffcanvasSidebar />}
    </Fragment>
  );
};

export default Header;
