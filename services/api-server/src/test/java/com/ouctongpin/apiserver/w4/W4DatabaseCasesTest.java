package com.ouctongpin.apiserver.w4;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ouctongpin.apiserver.auth.config.JwtUtil;
import com.ouctongpin.apiserver.auth.config.SecurityConfig;
import com.ouctongpin.apiserver.auth.mapper.UserMapper;
import com.ouctongpin.apiserver.checkin.controller.CheckinController;
import com.ouctongpin.apiserver.checkin.entity.Checkin;
import com.ouctongpin.apiserver.checkin.mapper.CheckinMapper;
import com.ouctongpin.apiserver.checkin.service.CheckinService;
import com.ouctongpin.apiserver.common.GlobalExceptionHandler;
import com.ouctongpin.apiserver.config.MybatisPlusConfig;
import com.ouctongpin.apiserver.moderation.ModerationClient;
import com.ouctongpin.apiserver.privacy.AnonymousIdGenerator;
import com.ouctongpin.apiserver.treehole.dto.PostCreateReq;
import com.ouctongpin.apiserver.treehole.entity.TreeholePost;
import com.ouctongpin.apiserver.treehole.scheduler.BurnTask;
import com.ouctongpin.apiserver.treehole.service.TreeholeService;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.SpyBean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.mockito.MockedStatic;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.SecureRandom;
import java.sql.Statement;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/** Explicit opt-in integration against the newly created W4 MySQL8/Redis stack. */
@EnabledIfEnvironmentVariable(named="W4_REAL_STACK", matches="true")
@SpringBootTest(classes=W4DatabaseCasesTest.Config.class, properties={
        "spring.main.banner-mode=off", "spring.sql.init.mode=never"})
@AutoConfigureMockMvc
@TestMethodOrder(MethodOrderer.MethodName.class)
class W4DatabaseCasesTest {
    @Configuration @EnableAutoConfiguration
    @MapperScan("com.ouctongpin.apiserver.**.mapper")
    @Import({SecurityConfig.class, JwtUtil.class, CheckinService.class, CheckinController.class,
            TreeholeService.class, BurnTask.class, MybatisPlusConfig.class,
            ModerationClient.class, AnonymousIdGenerator.class, GlobalExceptionHandler.class})
    static class Config {}
    @Autowired JdbcTemplate jdbc;
    @Autowired ObjectMapper json;
    @Autowired JwtUtil jwt;
    @Autowired MockMvc mvc;
    @Autowired org.mybatis.spring.SqlSessionTemplate sessions;
    @Autowired TreeholeService treehole;
    @Autowired BurnTask burn;
    @SpyBean UserMapper users;
    @SpyBean CheckinMapper checkinMapper;
    @SpyBean CheckinService checkins;
    @SpyBean StringRedisTemplate redis;
    static final String QUEUE="treehole:burn_queue";
    final List<Long> ownedPosts=new ArrayList<>();
    final List<Map<String,Object>> events=new ArrayList<>();
    String caseId;
    String startedAt;

    @BeforeEach void before(TestInfo info) {
        assertTrue(System.getenv("W4_PROJECT").startsWith("ouc-w4-new40-"));
        caseId=info.getTestMethod().orElseThrow().getName().substring(0,6).replace('_','-');
        startedAt=Instant.now().toString();
        reset(users,checkinMapper,checkins,redis);
        assertTrue(redis.opsForZSet().rangeByScore(QUEUE,0,System.currentTimeMillis()).isEmpty(),
                "Other due fixtures must be absent before a controlled scan");
    }
    @AfterEach void after() throws Exception {
        Path out=Path.of(System.getenv("W4_EVIDENCE_DIR"));Files.createDirectories(out);
        json.writerWithDefaultPrettyPrinter().writeValue(out.resolve(caseId+".json").toFile(),
                Map.of("case_id",caseId,"scope","real MySQL8/Redis; MockMvc explicitly identified",
                       "started_at_utc",startedAt,"finished_at_utc",Instant.now().toString(),"events",events));
        reset(users,checkinMapper,checkins,redis);
        for(long id:ownedPosts) redis.opsForZSet().remove(QUEUE,String.valueOf(id));
    }
    void record(String kind,Object value) {events.add(Map.of("kind",kind,"value",value));}
    long actor() {
        var key=new GeneratedKeyHolder();
        jdbc.update(c->{var st=c.prepareStatement("INSERT INTO users(nickname,deleted) VALUES (?,0)",
                Statement.RETURN_GENERATED_KEYS);st.setString(1,"w4-synthetic");return st;},key);
        return Objects.requireNonNull(key.getKey()).longValue();
    }
    long post(boolean anonymous) {
        var req=new PostCreateReq();req.setContent("w4-"+caseId+"-"+UUID.randomUUID());
        req.setEmotionTag("CALM");req.setAnonymous(anonymous);
        TreeholePost p=treehole.createPost(actor(),req);ownedPosts.add(p.getId());
        snapshot(p.getId());return p.getId();
    }
    void due(long id) {
        jdbc.update("UPDATE treehole_post SET expires_at='2000-01-01' WHERE id=?",id);
        redis.opsForZSet().add(QUEUE,String.valueOf(id),1);
    }
    Map<String,Object> snapshot(long id) {
        var p=jdbc.queryForMap("SELECT id,status,content,anonymous_id FROM treehole_post WHERE id=?",id);
        var result=new LinkedHashMap<String,Object>();result.put("post",p);
        result.put("identity_count",count("treehole_identity","post_id",id));
        result.put("archives",jdbc.queryForList("SELECT post_id,content_hash FROM treehole_archive WHERE post_id=?",id));
        result.put("queue_score",redis.opsForZSet().score(QUEUE,String.valueOf(id)));
        record("storage_snapshot",result);return result;
    }
    int count(String table,String key,long id) {
        assertTrue(Set.of("treehole_identity","treehole_archive","checkin").contains(table));
        return jdbc.queryForObject("SELECT COUNT(*) FROM "+table+" WHERE "+key+"=?",Integer.class,id);
    }
    String originalHash(long id) {
        String text=jdbc.queryForObject("SELECT content FROM treehole_post WHERE id=?",String.class,id);
        return org.springframework.util.DigestUtils.md5DigestAsHex(text.getBytes(StandardCharsets.UTF_8));
    }
    void burned(long id,int archives,String hash) {
        snapshot(id);
        var p=jdbc.queryForMap("SELECT status,content,anonymous_id FROM treehole_post WHERE id=?",id);
        assertEquals(1,((Number)p.get("status")).intValue());
        assertEquals("该内容已焚毁",p.get("content"));assertEquals("burned",p.get("anonymous_id"));
        assertEquals(0,count("treehole_identity","post_id",id));
        assertEquals(archives,count("treehole_archive","post_id",id));
        if(archives==1)assertEquals(hash,jdbc.queryForObject(
                "SELECT content_hash FROM treehole_archive WHERE post_id=?",String.class,id));
    }
    void absent(long id) {assertNull(redis.opsForZSet().score(QUEUE,String.valueOf(id)));}

    @Test void S1_085() {
        byte[] a=new byte[48],b=new byte[48];new SecureRandom().nextBytes(a);new SecureRandom().nextBytes(b);
        JwtUtil k1=new JwtUtil(Base64.getEncoder().encodeToString(a),120);
        JwtUtil k2=new JwtUtil(Base64.getEncoder().encodeToString(b),120);
        String t1=k1.generateToken(101L),t2=k2.generateToken(101L);
        assertEquals(101,k1.verify(t1));assertEquals(101,k2.verify(t2));
        assertThrows(io.jsonwebtoken.JwtException.class,()->k1.verify(t2));
        assertThrows(io.jsonwebtoken.JwtException.class,()->k2.verify(t1));
        record("instance_signature_matrix",Map.of("same_key",2,"cross_key_rejected",2,
                "http","N/A","mysql","N/A","redis","N/A"));
    }
    @Test void S1_087() throws Exception {
        long id=actor();String token=jwt.generateToken(id);
        int baseline=mvc.perform(get("/api/emotions/checkins").header("Authorization","Bearer "+token))
                .andReturn().getResponse().getStatus();assertEquals(200,baseline);
        clearInvocations(checkins);
        var failNext=new java.util.concurrent.atomic.AtomicBoolean(true);
        doAnswer(inv->{if(failNext.getAndSet(false))throw new DataAccessResourceFailureException("w4 injected");
            return sessions.getMapper(UserMapper.class).selectById(id);}).when(users).selectById(id);
        var failed=mvc.perform(get("/api/emotions/checkins").header("Authorization","Bearer "+token))
                .andReturn().getResponse();
        assertEquals(503,failed.getStatus());assertFalse(failed.getContentAsString().contains("injected"));
        verify(checkins,never()).list(anyLong(),any(),any());
        int recovered=mvc.perform(get("/api/emotions/checkins").header("Authorization","Bearer "+token))
                .andReturn().getResponse().getStatus();assertEquals(200,recovered);
        int anonymous=mvc.perform(get("/api/emotions/checkins")).andReturn().getResponse().getStatus();
        assertEquals(401,anonymous);
        record("mockmvc_statuses",List.of(baseline,failed.getStatus(),recovered,anonymous));
        record("owned_checkin_count",count("checkin","user_id",id));
    }
    @Test @SuppressWarnings("unchecked") void S1_098() throws Exception {
        long id=actor();var barrier=new CyclicBarrier(2);var first=ConcurrentHashMap.<Long>newKeySet();
        var duplicates=new AtomicInteger();
        CheckinMapper realMapper=sessions.getMapper(CheckinMapper.class);
        doAnswer(inv->{Checkin result=realMapper.selectOne((Wrapper<Checkin>)inv.getArgument(0));
            if(result==null&&Thread.currentThread().getName().startsWith("w4-race")&&
                    first.add(Thread.currentThread().getId()))barrier.await(10,TimeUnit.SECONDS);
            return result;}).when(checkinMapper).selectOne(any(Wrapper.class));
        doAnswer(inv->{try{return realMapper.insert((Checkin)inv.getArgument(0));}catch(DuplicateKeyException e){duplicates.incrementAndGet();throw e;}})
                .when(checkinMapper).insert(any(Checkin.class));
        ExecutorService pool=Executors.newFixedThreadPool(2,r->new Thread(r,"w4-race-"+UUID.randomUUID()));
        try {
            var a=pool.submit(()->checkins.doCheckin(id,"CALM",3,"race",LocalDate.of(2034,1,15)));
            var b=pool.submit(()->checkins.doCheckin(id,"CALM",3,"race",LocalDate.of(2034,1,15)));
            assertEquals(a.get(10,TimeUnit.SECONDS).getId(),b.get(10,TimeUnit.SECONDS).getId());
            assertEquals(1,duplicates.get());assertEquals(1,count("checkin","user_id",id));
            record("real_unique_key_race",Map.of("initial_null_queries",first.size(),
                    "duplicate_key_exceptions",duplicates.get(),"rows",1,"http","N/A"));
        } finally {barrier.reset();pool.shutdownNow();}
    }
    @Test void S1_100() {
        long p0=post(true),p1=post(true);LocalDateTime fixed=LocalDateTime.of(2034,1,15,10,0);
        jdbc.update("UPDATE treehole_post SET expires_at=? WHERE id=?",fixed,p0);
        jdbc.update("UPDATE treehole_post SET expires_at=? WHERE id=?",fixed.plusSeconds(1),p1);
        var before0=snapshot(p0);var before1=snapshot(p1);
        try(MockedStatic<LocalDateTime> clock=mockStatic(LocalDateTime.class,CALLS_REAL_METHODS)) {
            clock.when(()->LocalDateTime.now(ZoneOffset.ofHours(8))).thenReturn(fixed);
            var result=treehole.listPosts(null,null);
            @SuppressWarnings("unchecked") var items=(List<com.ouctongpin.apiserver.treehole.dto.PostResponse>)result.get("items");
            assertTrue(items.stream().noneMatch(p->p.getId().equals(p0)));
            assertTrue(items.stream().anyMatch(p->p.getId().equals(p1)));
            record("service_list_at_fixed_time",Map.of("equal_expiry_hidden",p0,"plus_one_visible",p1,"http","N/A"));
        }
        assertEquals(before0,snapshot(p0));assertEquals(before1,snapshot(p1));
    }
    @Test void S1_101() {
        for(boolean anonymous:List.of(true,false)) {
            long id=post(anonymous);String hash=originalHash(id);due(id);burn.scanAndBurn();
            burned(id,1,hash);absent(id);
            @SuppressWarnings("unchecked") var items=(List<com.ouctongpin.apiserver.treehole.dto.PostResponse>)treehole.listPosts(null,null).get("items");
            assertTrue(items.stream().noneMatch(p->p.getId().equals(id)));
        }
    }
    @Test @SuppressWarnings("unchecked") void S1_102() throws Exception {
        long id=post(true);String hash=originalHash(id);due(id);
        var operations=spy(redis.opsForZSet());doReturn(operations).when(redis).opsForZSet();
        var barrier=new CyclicBarrier(2);var claims=new AtomicInteger();
        doAnswer(inv->{Object found=inv.callRealMethod();claims.incrementAndGet();barrier.await(10,TimeUnit.SECONDS);return found;})
                .when(operations).rangeByScore(eq(QUEUE),eq(0d),anyDouble());
        var pool=Executors.newFixedThreadPool(2);
        try {
            Future<?> a=pool.submit(()->burn.scanAndBurn()),b=pool.submit(()->burn.scanAndBurn());
            a.get(10,TimeUnit.SECONDS);b.get(10,TimeUnit.SECONDS);
            assertEquals(2,claims.get());burned(id,1,hash);absent(id);
            record("worker_results",Map.of("successful_workers",2,"real_claims",claims.get()));
        } finally {barrier.reset();pool.shutdownNow();}
    }
    void ddl(String sql) throws Exception {
        try(var connection=java.sql.DriverManager.getConnection(System.getenv("DB_URL"),
                "root",System.getenv("MYSQL_ROOT_PASSWORD"));var statement=connection.createStatement()) {
            statement.setQueryTimeout(15);statement.execute(sql);
        }
        record("owned_guard_ddl",sql);
    }
    @Test void S1_103() throws Exception {
        long id=post(true);String hash=originalHash(id);due(id);var before=snapshot(id);
        String table="w4_guard_"+id;
        ddl("CREATE TABLE "+table+"(post_id BIGINT PRIMARY KEY,FOREIGN KEY(post_id) REFERENCES treehole_identity(post_id)) ENGINE=InnoDB");
        try {
            ddl("INSERT INTO "+table+" VALUES ("+id+")");
            assertThrows(RuntimeException.class,()->burn.scanAndBurn());
            assertEquals(before,snapshot(id));
        } finally {ddl("DROP TABLE "+table);}
        burn.scanAndBurn();burned(id,1,hash);absent(id);
    }
    @Test void S1_104() {
        long id=post(true);String hash=originalHash(id);due(id);
        var operations=spy(redis.opsForZSet());doReturn(operations).when(redis).opsForZSet();
        var attempts=new AtomicInteger();
        doAnswer(inv->{if(attempts.getAndIncrement()==0)throw new DataAccessResourceFailureException("w4 ack failure");
            return inv.callRealMethod();}).when(operations).remove(eq(QUEUE),eq(String.valueOf(id)));
        assertThrows(DataAccessResourceFailureException.class,()->burn.scanAndBurn());
        burned(id,1,hash);assertNotNull(redis.opsForZSet().score(QUEUE,String.valueOf(id)));
        burn.scanAndBurn();burned(id,1,hash);absent(id);record("ack_attempts",attempts.get());
    }
    @Test void S1_105() {
        long id=post(true);
        jdbc.update("UPDATE treehole_post SET status=1,content='该内容已焚毁' WHERE id=?",id);
        due(id);burn.scanAndBurn();burn.scanAndBurn();burned(id,0,null);absent(id);
    }
    @Test void S1_106() {
        long missing=post(true);jdbc.update("DELETE FROM treehole_identity WHERE post_id=?",missing);
        jdbc.update("DELETE FROM treehole_post WHERE id=?",missing);
        long valid=post(true);String hash=originalHash(valid);due(valid);
        redis.opsForZSet().add(QUEUE,String.valueOf(missing),1);
        record("missing_post_count",jdbc.queryForObject("SELECT COUNT(*) FROM treehole_post WHERE id=?",Integer.class,missing));
        burn.scanAndBurn();absent(missing);absent(valid);burned(valid,1,hash);
        assertEquals(0,count("treehole_archive","post_id",missing));
    }
}
