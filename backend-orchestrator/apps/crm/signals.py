"""
signals.py — CRM post-delete cleanup

When a Company is deleted, cascade-clean all associated data:
  - Leads (+ their Conversations + Messages via DB CASCADE)
  - NLUFallbackLogs are preserved (message FK becomes NULL)
  - ProductVector embeddings (products_vector table, vision-service)
  - Shop-specific ResponseTemplates
  - BotConfiguration
  - Redis template cache keys for this shop
"""
import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_delete, sender='crm.Company')
def cleanup_company_data(sender, instance, **kwargs):
    """
    Triggered after a Company is deleted from the DB.
    Cleans up all data belonging to the company's shop_id.
    NLUFallbackLog entries are preserved (message FK set to NULL by CASCADE rule).
    """
    from apps.crm.models import Lead, Conversation, ResponseTemplate, BotConfiguration, ProductVector

    shop_id = instance.shop_id
    if not shop_id:
        logger.warning("[SIGNAL] Company deleted but shop_id is empty — skipping cleanup")
        return

    logger.info(f"[SIGNAL] Company '{instance.name}' deleted — cleaning up shop_id={shop_id}")

    # ── 1. Leads → cascades Conversations → Messages → NLUFallbackLog (NULL) ──
    # Collect lead IDs via Conversations (covers leads where shop_id was not set)
    lead_ids_from_conversations = list(
        Conversation.objects.filter(shop_id=shop_id)
        .values_list('lead_id', flat=True)
        .distinct()
    )

    deleted_leads, _ = Lead.objects.filter(
        pk__in=lead_ids_from_conversations
    ).delete()
    logger.info(f"[SIGNAL] Deleted {deleted_leads} lead(s) (and their conversations/messages) for shop={shop_id}")

    # Also clean leads with shop_id set directly (e.g. progressive update)
    extra_leads, _ = Lead.objects.filter(shop_id=shop_id).delete()
    if extra_leads:
        logger.info(f"[SIGNAL] Deleted {extra_leads} additional lead(s) with shop_id={shop_id}")

    # ── 2. ProductVector embeddings (managed=False — vision-service table) ──
    try:
        deleted_vectors, _ = ProductVector.objects.filter(shop_id=shop_id).delete()
        logger.info(f"[SIGNAL] Deleted {deleted_vectors} product vector(s) for shop={shop_id}")
    except Exception as exc:
        logger.error(f"[SIGNAL] Failed to delete ProductVectors for shop={shop_id}: {exc}")

    # ── 3. Shop-specific ResponseTemplates (keep is_default=True system entries) ──
    deleted_templates, _ = ResponseTemplate.objects.filter(shop_id=shop_id).delete()
    logger.info(f"[SIGNAL] Deleted {deleted_templates} response template(s) for shop={shop_id}")

    # ── 4. BotConfiguration (Company.bot_config is SET_NULL, clean the orphan) ──
    deleted_configs, _ = BotConfiguration.objects.filter(shop_id=shop_id).delete()
    logger.info(f"[SIGNAL] Deleted {deleted_configs} bot configuration(s) for shop={shop_id}")

    # ── 5. Redis — purge template cache keys for this shop ────────────────────
    _clear_redis_cache(shop_id)


def _clear_redis_cache(shop_id: str):
    """
    Delete all Redis template cache keys for this shop (pattern: tmpl:{shop_id}:*).
    Uses the raw Redis client from Django's cache pool to avoid duplicating connection config.
    """
    try:
        from django.core.cache import cache

        # Django's built-in RedisCache exposes the underlying Redis client via _cache
        client = cache._cache.get_client(None)  # get the first (and only) client from the pool

        # Django key format (no KEY_PREFIX set): ":1:{key}" where 1 = KEY_VERSION default
        pattern = f":1:tmpl:{shop_id}:*"
        keys = list(client.scan_iter(match=pattern, count=100))
        if keys:
            client.delete(*keys)
            logger.info(f"[SIGNAL] Cleared {len(keys)} Redis cache key(s) for shop={shop_id}")
        else:
            logger.debug(f"[SIGNAL] No Redis cache keys found for shop={shop_id}")
    except Exception as exc:
        logger.warning(f"[SIGNAL] Redis cache cleanup failed for shop={shop_id}: {exc}")


from django.db.models.signals import post_save

@receiver(post_save, sender='crm.Company')
def initialize_company_setup(sender, instance, created, **kwargs):
    """
    Triggered when a Company is created or updated.
    If created:
      1. Generates a default BotConfiguration.
      2. Associates it with the Company.
      3. Syncs the catalog.
    """
    if created:
        from apps.crm.models import BotConfiguration
        from apps.gateway.services import tiktak_service
        from django.core.cache import cache

        logger.info(f"[SIGNAL] New Company '{instance.name}' created — initializing setup...")

        # 1. Create BotConfiguration
        # Avoid creating duplicate if shop_id somehow already exists
        bot_config, _ = BotConfiguration.objects.get_or_create(
            shop_id=instance.shop_id,
            defaults={
                'shop_name': instance.name,
                'ai_agent_name': 'Tiktak AI',
                'language': 'FR'
            }
        )

        # 2. Associate with Company
        instance.bot_config = bot_config
        instance.save(update_fields=['bot_config'])
        logger.info(f"[SIGNAL] Default BotConfiguration linked for shop={instance.shop_id}")

        # 3. Sync Catalog automatically
        try:
            # Clear old cache if it existed for any reason
            cache_key = f"tiktak_products:{instance.shop_id}"
            cache.delete(cache_key)
            
            # Fetch products from API
            tiktak_service.get_products(instance.shop_id)
            logger.info(f"[SIGNAL] Catalog sync triggered successfully for shop={instance.shop_id}")
        except Exception as e:
            logger.error(f"[SIGNAL] Failed to sync catalog for shop={instance.shop_id}: {e}")
