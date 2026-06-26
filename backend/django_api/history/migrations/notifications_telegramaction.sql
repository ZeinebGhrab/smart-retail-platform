-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Hôte : mysql:3306
-- Généré le : jeu. 25 juin 2026 à 18:53
-- Version du serveur : 8.0.40
-- Version de PHP : 8.2.26

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de données : `shopanalytics`
--

-- --------------------------------------------------------

--
-- Structure de la table `notifications_telegramaction`
--

CREATE TABLE `notifications_telegramaction` (
  `id` bigint NOT NULL,
  `video_code` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `camera_id` int DEFAULT NULL,
  `space_id` int DEFAULT NULL,
  `telegram_chat_id` bigint NOT NULL,
  `telegram_message_id` bigint NOT NULL,
  `telegram_user_id` bigint DEFAULT NULL,
  `telegram_username` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `action` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `created_at` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Déchargement des données de la table `notifications_telegramaction`
--

INSERT INTO `notifications_telegramaction` (`id`, `video_code`, `camera_id`, `space_id`, `telegram_chat_id`, `telegram_message_id`, `telegram_user_id`, `telegram_username`, `action`, `updated_at`, `created_at`) VALUES
(4428, 'Canal23_Aisle1_Rear_20260623-172349826570', 504, 49, -5028982501, 258204, 8582217642, 'Marc', 'false_alert', '2026-06-23 17:30:04.930055', '2026-06-23 17:30:04.930084'),
(4429, 'Canal13_Aisle2_Rear_Armex_20260623-171258456192', 525, 49, -5028982501, 258179, 8582217642, 'Marc', 'false_alert', '2026-06-23 17:30:28.467078', '2026-06-23 17:30:28.467108'),
(4430, 'Canal13_Aisle2_Rear_Armex_20260623-170029110051', 525, 49, -5028982501, 258157, 8582217642, 'Marc', 'suspicious', '2026-06-23 17:30:56.415828', '2026-06-23 17:30:56.415859'),
(4431, 'Canal23_Aisle1_Rear_20260623-170039050205', 504, 49, -5028982501, 258155, 8582217642, 'Marc', 'false_alert', '2026-06-23 17:32:07.407185', '2026-06-23 17:32:07.407218'),
(4432, 'Canal23_Aisle1_Rear_20260623-165947320061', 504, 49, -5028982501, 258153, 8582217642, 'Marc', 'suspicious', '2026-06-23 17:32:26.263853', '2026-06-23 17:32:26.263904'),
(4433, 'Canal12_Store_Rear_Overview_20260623-162500604946', 505, 49, -5028982501, 258104, 8582217642, 'Marc', 'false_alert', '2026-06-23 17:32:38.914958', '2026-06-23 17:32:38.914985'),
(4434, 'Canal12_Store_Rear_Overview_20260623-162150796764', 505, 49, -5028982501, 258100, 8582217642, 'Marc', 'false_alert', '2026-06-23 17:33:01.675473', '2026-06-23 17:33:01.675504'),
(4435, 'Cam_45_MG_Ennaser_20260622-173206245492', 542, 34, -4862083094, 257561, 5859359707, 'khalilaraar', 'false_alert', '2026-06-23 17:53:08.064015', '2026-06-23 17:53:08.064036'),
(4436, 'Cam_45_MG_Ennaser_20260622-193914052254', 542, 34, -4862083094, 257651, 5859359707, 'khalilaraar', 'false_alert', '2026-06-23 17:53:12.289342', '2026-06-23 17:53:12.289374'),
(4437, 'Carrefour_Paris_5_20260624-064246658092', 211, 10, -1002207307692, 28154, 5013753870, 'Ali', 'false_alert', '2026-06-24 06:43:44.170081', '2026-06-24 06:43:44.170107');

--
-- Index pour les tables déchargées
--

--
-- Index pour la table `notifications_telegramaction`
--
ALTER TABLE `notifications_telegramaction`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_telegram_chat_message` (`telegram_chat_id`,`telegram_message_id`),
  ADD KEY `notifications_telegramaction_video_code_63d4d0a7` (`video_code`),
  ADD KEY `notificatio_video_c_e03578_idx` (`video_code`),
  ADD KEY `notificatio_camera__226824_idx` (`camera_id`),
  ADD KEY `notificatio_space_i_35ddac_idx` (`space_id`),
  ADD KEY `notificatio_updated_f9c309_idx` (`updated_at`);

--
-- AUTO_INCREMENT pour les tables déchargées
--

--
-- AUTO_INCREMENT pour la table `notifications_telegramaction`
--
ALTER TABLE `notifications_telegramaction`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4438;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
