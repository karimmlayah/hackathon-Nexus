"use client";
//import node module libraries
import React, { Fragment } from "react";
import {
  Image,
  Accordion,
  ListGroup,
  Badge,
  Nav,
  NavItem,
  Button,
} from "react-bootstrap";
import Link from "next/link";
import { usePathname } from "next/navigation";

//import custom types
import { MenuItemType } from "types/menuTypes";

//import custom components
import CustomToggle, { CustomToggleLevel2 } from "./SidebarMenuToggle";
import { Avatar } from "components/common/Avatar";

// import required routes
import { DashboardMenu } from "routes/DashboardRoute";
import { getAssetPath } from "helper/assetPath";

interface SidebarProps {
  hideLogo: boolean;
  containerId?: string;
}
const Sidebar: React.FC<SidebarProps> = ({ hideLogo = false, containerId }) => {
  const location = usePathname();

  //Generate Link
  const generateLink = (item: MenuItemType) => {
    return (
      <Link
        href={`${item.link}`}
        className={`nav-link ${location === `/${item.link}` ? "active" : ""}`}
      >
        <span className="text">{item.name}</span>
        {item.badge && (
          <Badge
            className="ms-1"
            bg={item.badgecolor ? item.badgecolor : "primary"}
          >
            {item.badge}
          </Badge>
        )}
      </Link>
    );
  };

  return (
    <div id={containerId}>
      <div>
        {hideLogo || (
          <div className="brand-logo">
            <Link
              href="/"
              className="d-none d-md-flex align-items-center gap-2"
            >
              <Image src={getAssetPath("/images/brand/logo/logo-icon.svg")} alt="" />
              <span className="fw-bold fs-4 site-logo-text">FinFit</span>
            </Link>
          </div>
        )}

        {/* Sidebar Dashboard Menu */}
        <Accordion
          defaultActiveKey="0"
          as="ul"
          bsPrefix="navbar-nav flex-column"
        >
          {DashboardMenu.map(function (menu, index) {
            if (menu.grouptitle) {
              return (
                // Group Title
                <Nav.Item key={index} as="li">
                  <div className="nav-heading">{menu.title}</div>
                  <hr className="mx-5 nav-line mb-1" />
                </Nav.Item>
              );
            } else {
              if (menu.children) {
                return (
                  <Fragment key={index}>
                    {/* Dropdown Parent Menu */}
                    <CustomToggle eventKey={index.toString()} icon={menu.icon}>
                      {menu.title}
                    </CustomToggle>
                    <Accordion.Collapse eventKey={index.toString()}>
                      <ListGroup as="ul" className="dropdown-menu flex-column">
                        {menu.children.map(function (
                          menuLevel1Item,
                          menuLevel1Index
                        ) {
                          if (menuLevel1Item.children) {
                            return (
                              <ListGroup.Item
                                as="li"
                                bsPrefix="nav-item"
                                key={menuLevel1Index}
                              >
                                {/* first level menu started  */}
                                <Accordion
                                  defaultActiveKey="0"
                                  bsPrefix="navbar-nav flex-column"
                                >
                                  <CustomToggleLevel2
                                    eventKey={"0"}
                                    href={"#link"}
                                  >
                                    {menuLevel1Item.title}
                                  </CustomToggleLevel2>
                                  <Accordion.Collapse eventKey={"0"}>
                                    <ListGroup
                                      as="ul"
                                      bsPrefix=""
                                      className="nav flex-column"
                                    >
                                      {/* second level menu started  */}
                                      {menuLevel1Item.children.map(function (
                                        menuLevel2Item,
                                        menuLevel2Index
                                      ) {
                                        if (menuLevel2Item.children) {
                                          return (
                                            <ListGroup.Item
                                              as="li"
                                              bsPrefix="nav-item"
                                              key={menuLevel2Index}
                                            >
                                              {/* second level accordion menu started  */}
                                              <Accordion
                                                defaultActiveKey="0"
                                                className="navbar-nav flex-column"
                                              >
                                                <CustomToggleLevel2
                                                  eventKey={"0"}
                                                >
                                                  {menuLevel2Item.title}
                                                </CustomToggleLevel2>
                                                <Accordion.Collapse
                                                  eventKey={"0"}
                                                  bsPrefix="nav-item"
                                                >
                                                  <ListGroup
                                                    as="ul"
                                                    bsPrefix=""
                                                    className="nav flex-column"
                                                  >
                                                    {/* third level menu started  */}
                                                    {menuLevel2Item.children.map(
                                                      function (
                                                        menuLevel3Item,
                                                        menuLevel3Index
                                                      ) {
                                                        return (
                                                          <ListGroup.Item
                                                            key={
                                                              menuLevel3Index
                                                            }
                                                            as="li"
                                                            bsPrefix="nav-item"
                                                          >
                                                            <Link
                                                              href={
                                                                menuLevel3Item.link?.toString() ||
                                                                `/${menuLevel3Item.link}`
                                                              }
                                                              className={`nav-link ${location ===
                                                                `/${menuLevel3Item.link}`
                                                                ? "active"
                                                                : ""
                                                                }`}
                                                            >
                                                              {
                                                                menuLevel3Item.name
                                                              }
                                                            </Link>
                                                          </ListGroup.Item>
                                                        );
                                                      }
                                                    )}
                                                    {/* end of third level menu  */}
                                                  </ListGroup>
                                                </Accordion.Collapse>
                                              </Accordion>
                                              {/* end of second level accordion */}
                                            </ListGroup.Item>
                                          );
                                        } else {
                                          return (
                                            <ListGroup.Item
                                              key={menuLevel2Index}
                                              as="li"
                                              bsPrefix="nav-item"
                                            >
                                              {generateLink(menuLevel2Item)}
                                            </ListGroup.Item>
                                          );
                                        }
                                      })}
                                      {/* end of second level menu  */}
                                    </ListGroup>
                                  </Accordion.Collapse>
                                </Accordion>
                                {/* end of first level menu */}
                              </ListGroup.Item>
                            );
                          } else {
                            return (
                              <ListGroup.Item
                                as="li"
                                bsPrefix="nav-item"
                                key={menuLevel1Index}
                              >
                                {/* first level menu items */}
                                <Link
                                  href={`/${menuLevel1Item?.link}`}
                                  className={`nav-link ${location === `/${menuLevel1Item.link}`
                                    ? "active"
                                    : ""
                                    }`}
                                >
                                  {menuLevel1Item.name}
                                </Link>
                                {/* end of first level menu items */}
                              </ListGroup.Item>
                            );
                          }
                        })}
                      </ListGroup>
                    </Accordion.Collapse>
                    {/* end of main menu / menu level 1 / root items */}
                  </Fragment>
                );
              } else {
                return (
                  <Nav.Item as="li" key={index}>
                    <Link
                      href={menu.link ? `${menu.link}` : "#"}
                      className={`nav-link ${location === menu.link ? "active" : ""
                        }`}
                    >
                      <span className="nav-icon me-3">{menu.icon}</span>
                      <span className="text">{menu.title}</span>
                    </Link>
                  </Nav.Item>
                );
              }
            }
          })}

        </Accordion>
      </div>
    </div>
  );
};

export default Sidebar;
