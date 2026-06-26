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
-- Structure de la table `notifications_space`
--

CREATE TABLE `notifications_space` (
  `id` bigint NOT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `create_date` datetime(6) NOT NULL,
  `update_date` datetime(6) NOT NULL,
  `address` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `city` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `code` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `country` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `organization_id` bigint NOT NULL,
  `telegram_chat_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `language` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `token_web_connector` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `url_web_connector` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `send_telegram_message` tinyint(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Déchargement des données de la table `notifications_space`
--

INSERT INTO `notifications_space` (`id`, `name`, `create_date`, `update_date`, `address`, `city`, `code`, `country`, `organization_id`, `telegram_chat_id`, `language`, `token_web_connector`, `url_web_connector`, `send_telegram_message`) VALUES
(1, 'ShoppingClub', '2023-12-20 07:59:42.681411', '2026-02-19 07:49:01.877591', 'sfax, sakit ezzit', 'sfax', '5987654', 'tunisia', 1, '-4165761097,-1003251500741', 'fr', NULL, NULL, 1),
(3, 'Bricorama_Pantin', '2023-12-20 08:58:29.165909', '2026-02-19 07:48:52.966348', 'Bricorama Paris. 27 Avenue Jean Jaurès', 'paris', 'B11-B1', 'france', 3, '-896569267,-1003251500741', 'fr', NULL, NULL, 1),
(4, 'Pharmacie_Boulogne', '2023-12-24 17:41:05.329673', '2026-02-19 06:47:33.294305', 'paris', 'paris', '64754', 'france', 4, '-957530583,-4917494366', 'fr', NULL, NULL, 1),
(5, 'Famiflora', '2024-01-11 14:00:48.157757', '2026-02-19 07:48:41.181836', 'paris', 'paris', '435621', 'france', 5, '-4011300981,-1003251500741', 'fr', NULL, NULL, 1),
(7, 'Anavid', '2024-03-29 09:17:58.250206', '2026-02-19 07:48:32.466594', 'sfax, sakit ezzit', 'Sfax', '29969787', 'Tunisia', 9, '-1001498104554', 'fr', '1069002b8374962bd47222e47d3d94864ca33d1e', 'http://20.61.40.233:3000', 1),
(8, 'Hikvision', '2024-07-04 14:53:29.074164', '2026-02-27 09:15:55.665528', 'Paris', 'Paris', '435621', 'France', 10, '-5070877950', 'fr', NULL, NULL, 1),
(9, 'Newrest', '2024-08-01 13:46:38.763827', '2025-11-04 17:38:50.715593', 'Route Agareb Sfax N Ord', 'Sfax', '00000', 'Sfax', 11, '-1002417843311,-4917494366', 'fr', '1069002b8374962bd47222e47d3d94864ca33d1e', 'https://app.shoplifting.admin.anavid.co/', 1),
(10, 'Carrefour_Paris', '2024-08-23 14:03:47.150252', '2026-02-19 07:48:17.346279', 'Paris', 'Paris', '123456', 'France', 12, '-1002207307692,-1003251500741', 'fr', NULL, NULL, 1),
(11, 'Altertline_security', '2024-10-10 13:43:14.394058', '2025-11-04 17:38:37.869026', 'ireland', 'ireland', '08879738', 'ireland', 13, '-4542229204,-4917494366', 'en', '1069002b8374962bd47222e47d3d94864ca33d1e', 'https://app.shoplifting.admin.anavid.co/', 1),
(13, 'test-fr', '2024-10-16 09:42:42.382044', '2026-02-09 14:19:28.088477', 'sfax', 'Sfax', '56588', 'Tunisia', 9, '-004547185536,-4917494366,', 'fr', '1069002b8374962bd47222e47d3d94864ca33d1e', 'https://app.shoplifting.admin.anavid.co/', 1);

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
