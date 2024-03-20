import React, { useEffect, useState } from "react";
import { BuilderComponent, builder, useIsPreviewing } from "@builder.io/react";
import "./App.css";

builder.init("d3359313752844e5b43d36d99db54022");

export default function CatchAllRoute() {
  const isPreviewingInBuilder = useIsPreviewing();
  const [notFound, setNotFound] = useState(false);
  const [content, setContent] = useState(null);
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(true); // Added loading state

  useEffect(() => {
    async function fetchContent() {
      const contentResponse = await builder
        .get("page", {
          url: window.location.pathname,
        })
        .promise();
      setContent(contentResponse);
      setNotFound(!contentResponse);

      if (contentResponse?.data.title) {
        document.title = contentResponse.data.title;
      }
    }

    async function fetchData() {
      const response = await fetch("/api/data");
      const fetchedData = await response.json();
      setData(fetchedData);
      setLoading(false); // Data has been fetched
    }

    fetchContent();
    fetchData();
  }, [window.location.pathname]);

  if (loading) {
    return <div>Loading...</div>; // Show loading message while fetching data
  }

  if (notFound && !isPreviewingInBuilder) {
    return <div>404 Page Not Found</div>; // Show 404 message if not found
  }

  // Extract the data into variables after fetching
  const currentUser = data.current_user && {
    avatarUrl: data.current_user.avatar_url,
    discriminator: data.current_user.discriminator,
    email: data.current_user.email,
    hasMfaEnabled: data.current_user.has_mfa_enabled,
    id: data.current_user.id,
    isVerified: data.current_user.is_verified,
    locale: data.current_user.locale,
    username: data.current_user.username,
  };

  const playerCount = data.playercount;
  const serverCount = data.servercount;
  const achievementCount = data.achievementcount;

  console.log(
    `Current User: ${currentUser ? currentUser.username : "guest"} (${
      currentUser ? currentUser.id : "0"
    }), Player Count: ${playerCount}, Server Count: ${serverCount}, Achievement Count: ${achievementCount}`
  );

  return (
    <>
      {/* Render the Builder page with received data */}
      <BuilderComponent
        model="page"
        data={{
          currentUser,
          playerCount,
          serverCount,
          achievementCount,
        }}
        content={content}
      />
    </>
  );
}
