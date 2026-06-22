/**
 * Render config. Node APIs do not read this file, so the bridge passes the
 * same options directly when it renders.
 */
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
