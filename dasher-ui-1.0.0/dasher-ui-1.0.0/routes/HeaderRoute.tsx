//import node modules libraries
import { v4 as uuid } from "uuid";
import {
  IconHome2,
  IconSettings,
} from "@tabler/icons-react";

export const UserMenuItem = [
  {
    id: uuid(),
    link: "/",
    title: "Home",
    icon: <IconHome2 size={20} strokeWidth={1.5} />,
  },
  {
    id: uuid(),
    link: "/settings",
    title: "Settings",
    icon: <IconSettings size={20} strokeWidth={1.5} />,
  },
];
