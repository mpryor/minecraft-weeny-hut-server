import com.hypherionmc.craterlib.libs.moonconfig.core.file.CommentedFileConfig;
import com.hypherionmc.craterlib.libs.moonconfig.core.conversion.ObjectConverter;
import java.io.File;
import java.io.IOException;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;

/**
 * Emits sdlink's complete default config with the three values we control replaced by
 * CFG_ placeholders, for the container to interpolate from the ECS task definition.
 *
 * Why the file has to be complete, rather than the four lines we actually care about:
 * CraterLib loads it with ObjectConverter.toObject, which walks the config POJO's
 * fields and assigns config.get(fieldName) to each one. A key missing from the file
 * comes back null, and a primitive field then throws -- "Can not set boolean field
 * GeneralConfigSettings.debugging to null value". So every key sdlink knows about has
 * to be present.
 *
 * Why we cannot instead let the migrator fill the gaps: setting general.configVersion
 * below sdlink's own (37) sends SDLinkConfig.migrateConfig down the upgrade path, and
 * its oldVersion < 21 step is
 *
 *     cfg.set("botConfig.botStatus", Collections.singletonList(old.get("botConfig.botStatus")))
 *
 * On a file with no botConfig.botStatus that is singletonList(null), and CraterLib's
 * TOML writer refuses it -- "TOML doesn't support null values" -- after it has already
 * truncated the file. The result is a zero-byte config and a disabled mod.
 *
 * Pinning the current version means no migration runs today, and a future sdlink that
 * bumps to 38 migrates from 37, where neither that step nor the < 27 one fires.
 *
 * Run via scripts/gen-sdlink-config.sh, which supplies the jars on the classpath.
 */
public class GenSdlinkConfig {

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("usage: GenSdlinkConfig <output.toml>");
            System.exit(2);
        }

        int configVer = Class.forName("com.hypherionmc.sdlink.core.config.SDLinkConfig")
                             .getDeclaredField("configVer")
                             .getInt(null);

        File out = new File(args[0]);
        if (out.exists() && !out.delete()) {
            throw new IOException("could not remove " + out);
        }

        CommentedFileConfig cfg = CommentedFileConfig.builder(out).sync().build();
        new ObjectConverter().toConfig(defaults(), cfg);

        cfg.set("general.configVersion", configVer);
        cfg.set("botConfig.botToken", "${CFG_SDLINK_BOT_TOKEN}");
        cfg.set("channelsAndWebhooks.serverName", "${CFG_SDLINK_SERVER_NAME}");
        cfg.set("channelsAndWebhooks.channels.chatChannelID", "${CFG_SDLINK_CHAT_CHANNEL_ID}");
        cfg.save();
        cfg.close();

        verify(out);
        System.out.println("wrote " + out + " at configVersion " + configVer);
    }

    /**
     * SDLinkConfig's constructor sets every section to a new instance and then calls
     * registerAndSetup, which reads and writes real files. Allocate the instance without
     * running it and populate the sections the same way it would.
     */
    private static Object defaults() throws Exception {
        Field theUnsafe = sun.misc.Unsafe.class.getDeclaredField("theUnsafe");
        theUnsafe.setAccessible(true);
        sun.misc.Unsafe unsafe = (sun.misc.Unsafe) theUnsafe.get(null);

        Class<?> type = Class.forName("com.hypherionmc.sdlink.core.config.SDLinkConfig");
        Object config = unsafe.allocateInstance(type);

        for (Field field : type.getDeclaredFields()) {
            if (Modifier.isStatic(field.getModifiers()) || Modifier.isTransient(field.getModifiers())) {
                continue;
            }
            field.setAccessible(true);
            Constructor<?> ctor = field.getType().getDeclaredConstructor();
            ctor.setAccessible(true);
            field.set(config, ctor.newInstance());
        }
        return config;
    }

    /** The load path the mod itself takes. Throws here rather than on the server. */
    private static void verify(File out) throws Exception {
        CommentedFileConfig back = CommentedFileConfig.builder(out).sync().build();
        back.load();
        new ObjectConverter().toObject(back, defaults());
        back.close();
    }
}
