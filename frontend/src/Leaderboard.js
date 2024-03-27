import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";

import "./index.css";
import { BuilderComponent, builder, useIsPreviewing } from "@builder.io/react";
import "@builder.io/widgets";

builder.init("d3359313752844e5b43d36d99db54022");

function Leaderboard() {
  const isPreviewingInBuilder = useIsPreviewing();
  const [notFound, setNotFound] = useState(false);
  const [content, setContent] = useState(null);
  const [data, setData] = useState({});
  const [lbdata, setLbData] = useState({});
  const [loading, setLoading] = useState(true);

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
      const lbresponse = await fetch("/api/leaderboard");
      const fetchedData = await response.json();
      const fetchedLbData = await lbresponse.json();
      setData(fetchedData);
      setLbData(fetchedLbData);
      setLoading(false);
    }

    fetchContent();
    fetchData();
  }, [window.location.pathname]);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <img
          src="/loading.gif"
          alt="Loading..."
          style={{
            width: "40px",
            height: "40px",
            animation: "spin 2s linear infinite",
          }}
        />
      </div>
    );
  }

  if (notFound && !isPreviewingInBuilder) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <h1>404 Page Not Found</h1>
      </div>
    );
  }

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

  const currentPlayer = {
    id: data.player.id,
    username: data.player.username,
    displayname: data.player.displayname,
    cultivationLevel: data.player.cultivation_level,
    balance: data.player.bal,
    usingCommand: data.player.using_command,
    tutorial: data.player.tutorial,
    finishedTutorial: data.player.finished_tutorial,
    createdAt: data.player.created_at,
    deaths: data.player.deaths,
    dmCommands: data.player.dm_cmds,
    helper: data.player.helper,
    moderator: data.player.moderator,
    admin: data.player.admin,
    heartDemons: data.player.heart_demons,
    yearsSpent: data.player.years_spent,
    fastestYearScore: data.player.fastest_year_score,
    maxCultivationAttained: data.player.max_cultivation_attained,
    ascensions: data.player.ascensions,
  };

  const leaderboard = {
    mortal: lbdata.ascended,
    immortal: lbdata.immortal,
    ascended: lbdata.ascended,
    deceased: lbdata.deceased,
  };

  return (
    <BuilderComponent
      model="page"
      data={{
        leaderboard,
        currentPlayer,
        currentUser,
        playerCount: data.playercount,
        serverCount: data.servercount,
        achievementCount: data.achievementcount,
      }}
      content={content}
    />
  );
}

export default Leaderboard;
