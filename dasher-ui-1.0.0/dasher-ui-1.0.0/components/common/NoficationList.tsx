"use client";
//import node modules libraries
import SimpleBar from "simplebar-react";
import { ListGroup, Nav, Offcanvas, Tab, Button } from "react-bootstrap";
import Link from "next/link";

//import custom components
import Flex from "./Flex";
import {
  IconCalendarWeek,
  IconChecks,
  IconCircleFilled,
  IconSettings,
  IconShoppingCart,
} from "@tabler/icons-react";
import { Avatar } from "./Avatar";

interface NotificationProps {
  isOpen: boolean;
  onClose: () => void;
}

const NoficationList: React.FC<NotificationProps> = ({ isOpen, onClose }) => {
  return (
    <Offcanvas placement="end" show={isOpen} onHide={onClose}>
      <div className="sticky-top bg-white">
        <Offcanvas.Header className="gap-4" closeButton={true}>
          <Flex justifyContent="between" className="w-100">
            <h5 className="mb-0" id="offcanvasNotificationLabel">
              Notifications
            </h5>
            <Flex alignItems="center" className="gap-3">
              <Link href="#" className="link-primary">
                <IconChecks size={24} strokeWidth={1.5} />
              </Link>
              <Link href="#" className="text-inherit">
                <IconSettings size={24} strokeWidth={1.5} />
              </Link>
            </Flex>
          </Flex>
        </Offcanvas.Header>
      </div>

      {/* Tab Content Start */}
      <div className="mt-2">
        <Tab.Container defaultActiveKey={"0"}>
          <Nav className="nav-line-bottom" defaultActiveKey={"0"}>
            <Nav.Item>
              <Nav.Link role="button" eventKey={"0"}>
                All
              </Nav.Link>
            </Nav.Item>
            <Nav.Item>
              <Nav.Link role="button" eventKey={"1"}>
                Following
              </Nav.Link>
            </Nav.Item>
            <Nav.Item>
              <Nav.Link role="button" eventKey={"2"}>
                Archive
              </Nav.Link>
            </Nav.Item>
          </Nav>
          <Tab.Content id="pills-tabContent">
            <Tab.Pane eventKey={"0"}>
              <SimpleBar style={{ maxHeight: 450 }}>
                <ListGroup variant="flush">
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex flex-column gap-1">
                        <div>New message from John Doe</div>
                        <small className="text-secondary">2 minutes ago</small>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex flex-column gap-1">
                        <div>Your password will expire soon.</div>
                        <small className="text-secondary">2 minutes ago</small>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex gap-4 align-items-center">
                        <Avatar
                          type="image"
                          src="/images/avatar/avatar-1.jpg"
                          size="md"
                          className="rounded-circle"
                        />
                        <div className="d-flex flex-column gap-1">
                          <div>Alice uploaded a new profile picture.</div>
                          <small className="text-secondary">1 hour ago</small>
                        </div>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex gap-4 align-items-center">
                        <Avatar
                          type="image"
                          src="/images/avatar/avatar-2.jpg"
                          size="md"
                          className="rounded-circle"
                        />
                        <div className="d-flex flex-column gap-1">
                          <div>Mike sent you a friend request.</div>
                          <small className="text-secondary">
                            5 minutes ago
                          </small>
                        </div>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                    <div className="d-flex gap-2 align-items-center mt-4">
                      <Button href="#" variant="primary" size="sm">
                        Accept
                      </Button>
                      <Button href="#" variant="white" size="sm">
                        Decline
                      </Button>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex gap-4 align-items-center">
                        <Avatar
                          type="image"
                          src="/images/avatar/avatar-3.jpg"
                          size="md"
                          className="rounded-circle"
                        />
                        <div className="d-flex flex-column gap-1">
                          <div>Sophia commented on your post.</div>
                          <small className="text-secondary">
                            20 minutes ago
                          </small>
                        </div>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex gap-4 align-items-center">
                        <div className="icon-shape icon-md bg-primary-subtle text-primary-emphasis rounded-circle d-flex align-items-center justify-content-center">
                          <IconSettings size={20} stroke={1.5} />
                        </div>
                        <div className="d-flex flex-column gap-1">
                          <div>A system update has been installed.</div>
                          <small className="text-secondary">
                            30 minutes ago
                          </small>
                        </div>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex gap-4 align-items-center">
                        <div className="icon-shape icon-md bg-info-subtle text-info-emphasis rounded-circle d-flex align-items-center justify-content-center">
                          <IconCalendarWeek size={20} stroke={1.5} />
                        </div>
                        <div className="d-flex flex-column gap-1">
                          <div>Reminder: Team meeting at 3:00 PM.</div>
                          <small className="text-secondary">1 hour ago</small>
                        </div>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex gap-4 align-items-center">
                        <div className="icon-shape icon-md bg-danger-subtle text-danger-emphasis rounded-circle d-flex align-items-center justify-content-center">
                          <IconShoppingCart size={20} stroke={1.5} />
                        </div>
                        <div className="d-flex flex-column gap-1">
                          <div>Your order has been shipped!</div>
                          <small className="text-secondary">2 hour ago</small>
                        </div>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                  </ListGroup.Item>
                </ListGroup>
              </SimpleBar>
            </Tab.Pane>
            <Tab.Pane eventKey={"1"}>
              <SimpleBar style={{ maxHeight: 450 }}>
                <ListGroup variant="flush">
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex gap-4 align-items-center">
                        <div className="icon-shape icon-md bg-info-subtle text-info-emphasis rounded-circle d-flex align-items-center justify-content-center">
                          <IconCalendarWeek size={20} stroke={1.5} />
                        </div>
                        <div className="d-flex flex-column gap-1">
                          <div>Reminder: Team meeting at 3:00 PM.</div>
                          <small className="text-secondary">1 hour ago</small>
                        </div>
                      </div>

                      <div>
                        <IconCircleFilled
                          size={10}
                          color="currentColor"
                          className="text-info"
                        />
                      </div>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex gap-4 align-items-center">
                        <div className="icon-shape icon-md bg-danger-subtle text-danger-emphasis rounded-circle d-flex align-items-center justify-content-center">
                          <IconShoppingCart size={20} stroke={1.5} />
                        </div>
                        <div className="d-flex flex-column gap-1">
                          <div>Your order has been shipped!</div>
                          <small className="text-secondary">2 hour ago</small>
                        </div>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex gap-4 align-items-center">
                        <Avatar
                          type="image"
                          src="/images/avatar/avatar-3.jpg"
                          size="md"
                          className="rounded-circle"
                        />
                        <div className="d-flex flex-column gap-1">
                          <div>Sophia commented on your post.</div>
                          <small className="text-secondary">
                            20 minutes ago
                          </small>
                        </div>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex gap-4 align-items-center">
                        <div className="icon-shape icon-md bg-primary-subtle text-primary-emphasis rounded-circle d-flex align-items-center justify-content-center">
                          <IconSettings size={20} stroke={1.5} />
                        </div>
                        <div className="d-flex flex-column gap-1">
                          <div>A system update has been installed.</div>
                          <small className="text-secondary">
                            30 minutes ago
                          </small>
                        </div>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex gap-4 align-items-center">
                        <div className="icon-shape icon-md bg-info-subtle text-info-emphasis rounded-circle d-flex align-items-center justify-content-center">
                          <IconCalendarWeek size={20} stroke={1.5} />
                        </div>
                        <div className="d-flex flex-column gap-1">
                          <div>Reminder: Team meeting at 3:00 PM.</div>
                          <small className="text-secondary">1 hour ago</small>
                        </div>
                      </div>

                      <div>
                        <IconCircleFilled
                          size={10}
                          color="currentColor"
                          className="text-info"
                        />
                      </div>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex gap-4 align-items-center">
                        <div className="icon-shape icon-md bg-danger-subtle text-danger-emphasis rounded-circle d-flex align-items-center justify-content-center">
                          <IconShoppingCart size={20} stroke={1.5} />
                        </div>
                        <div className="d-flex flex-column gap-1">
                          <div>Your order has been shipped!</div>
                          <small className="text-secondary">2 hour ago</small>
                        </div>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                  </ListGroup.Item>
                </ListGroup>
              </SimpleBar>
            </Tab.Pane>
            <Tab.Pane eventKey={"2"}>
              <SimpleBar style={{ maxHeight: 450 }}>
                <ListGroup variant="flush">
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex flex-column gap-1">
                        <div>New message from John Doe</div>
                        <small className="text-secondary">2 minutes ago</small>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex flex-column gap-1">
                        <div>Your password will expire soon.</div>
                        <small className="text-secondary">2 minutes ago</small>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex gap-4 align-items-center">
                        <Avatar
                          type="image"
                          src="/images/avatar/avatar-1.jpg"
                          size="md"
                          className="rounded-circle"
                        />
                        <div className="d-flex flex-column gap-1">
                          <div>Alice uploaded a new profile picture.</div>
                          <small className="text-secondary">1 hour ago</small>
                        </div>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                  </ListGroup.Item>
                  <ListGroup.Item
                    action
                    className="p-5 border-dashed border-bottom"
                  >
                    <div className="d-flex justify-content-between">
                      <div className="d-flex gap-4 align-items-center">
                        <Avatar
                          type="image"
                          src="/images/avatar/avatar-2.jpg"
                          size="md"
                          className="rounded-circle"
                        />
                        <div className="d-flex flex-column gap-1">
                          <div>Mike sent you a friend request.</div>
                          <small className="text-secondary">
                            5 minutes ago
                          </small>
                        </div>
                      </div>
                      <div>
                        <IconCircleFilled size={10} className="text-info" />
                      </div>
                    </div>
                    <div className="d-flex gap-2 align-items-center mt-4">
                      <Button href="#" variant="primary" size="sm">
                        Accept
                      </Button>
                      <Button href="#" variant="white" size="sm">
                        Decline
                      </Button>
                    </div>
                  </ListGroup.Item>
                </ListGroup>
              </SimpleBar>
            </Tab.Pane>
          </Tab.Content>
        </Tab.Container>
      </div>
      <div className="px-5 py-3 text-center bg-white position-absolute bottom-0 border-top border-dashed w-100 text-center">
        <Link href="#!" className="text-inherit">
          View all
        </Link>
      </div>
    </Offcanvas>
  );
};

export default NoficationList;
