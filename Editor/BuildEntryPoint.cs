#if UNITY_EDITOR

using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace KUnityYamae.Editor
{
    public static class BuildEntryPoint
    {
        public static void Build()
        {
            var args = Environment.GetCommandLineArgs();
            var targetName = ReadArg(args, "-kunityBuildTarget", "StandaloneWindows64");
            var outputPath = ReadArg(args, "-kunityBuildOutput", "Builds/KUnityYamaeBuild.exe");

            if (!Enum.TryParse(targetName, out BuildTarget buildTarget))
            {
                Debug.LogError($"[KUnityYamae] Unknown build target: {targetName}");
                EditorApplication.Exit(1);
                return;
            }

            var scenes = EditorBuildSettings.scenes
                .Where(scene => scene.enabled)
                .Select(scene => scene.path)
                .Where(path => !string.IsNullOrEmpty(path))
                .ToArray();

            if (scenes.Length == 0)
            {
                Debug.LogError("[KUnityYamae] No enabled scenes are configured for build.");
                EditorApplication.Exit(1);
                return;
            }

            var outputDirectory = Path.GetDirectoryName(outputPath);
            if (!string.IsNullOrEmpty(outputDirectory))
            {
                Directory.CreateDirectory(outputDirectory);
            }

            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = scenes,
                locationPathName = outputPath,
                target = buildTarget,
                options = BuildOptions.None,
            });

            if (report.summary.result == BuildResult.Succeeded)
            {
                Debug.Log($"[KUnityYamae] Build succeeded: {outputPath}");
                EditorApplication.Exit(0);
                return;
            }

            Debug.LogError($"[KUnityYamae] Build failed: {report.summary.result}");
            EditorApplication.Exit(1);
        }

        private static string ReadArg(string[] args, string name, string fallback)
        {
            for (var index = 0; index < args.Length - 1; index++)
            {
                if (args[index] == name)
                {
                    return args[index + 1];
                }
            }

            return fallback;
        }
    }
}

#endif
